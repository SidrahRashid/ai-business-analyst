"""
DYNAMIC BUSINESS GLOSSARY & ENTERPRISE JARGON REGISTRY
======================================================
Enables business users and data teams to configure custom terminology,
company-specific abbreviations, and analytical formulas dynamically.
Bypasses static hardcoding and enriches both local NLP and LLM planning.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

GLOSSARY_DIR = Path(__file__).resolve().parent / "data" / "glossary"
GLOSSARY_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_GLOSSARY: Dict[str, Dict[str, Any]] = {
    "client_alpha": {
        "client_name": "Himalayan Estate Teas & Auctions",
        "aliases": {
            "realized gross inflow": "TOTAL_REVENUE_USD",
            "gross turnover": "TOTAL_REVENUE_USD",
            "auction proceeds": "TOTAL_REVENUE_USD",
            "net payload": "VOLUME_KG",
            "harvest payload": "VOLUME_KG",
            "crop weight": "VOLUME_KG",
            "tea garden": "ESTATE",
            "gardens": "ESTATE",
            "plantation": "ESTATE",
            "plucking run": "SEASON_FLUSH",
            "flush season": "SEASON_FLUSH",
            "cupping rating": "QUALITY_SCORE",
            "cupping score": "QUALITY_SCORE",
            "cupping benchmark": "QUALITY_SCORE",
            "cupping": "QUALITY_SCORE",
            "moisture content": "MOISTURE_PCT",
            "leaf moisture": "MOISTURE_PCT",
            "clearing price": "PRICE_PER_KG_USD",
            "hammer price": "PRICE_PER_KG_USD",
            "transit lag": "DAYS_IN_TRANSIT",
            "shipping lead time": "DAYS_IN_TRANSIT",
            "carrier line": "LOGISTICS_CARRIER",
            "importer nation": "BUYER_COUNTRY",
        },
        "formulas": {
            "effective_yield": {
                "description": "Calculates revenue realization per kilogram",
                "formula": "TOTAL_REVENUE_USD / VOLUME_KG",
                "target_type": "measure",
            },
            "transit_efficiency": {
                "description": "Measures transit speed against baseline of 30 days",
                "formula": "30 - DAYS_IN_TRANSIT",
                "target_type": "metric",
            }
        }
    },
    "client_beta": {
        "client_name": "Zenith Artisanal Blends & Retail",
        "aliases": {
            "realized turnover": "NET_SALES_USD",
            "top line sales": "NET_SALES_USD",
            "gross proceeds": "NET_SALES_USD",
            "gross margin spread": "GROSS_MARGIN_PCT",
            "margin pct": "GROSS_MARGIN_PCT",
            "blend label": "PRODUCT_NAME",
            "tea blend": "PRODUCT_NAME",
            "merchandise type": "CATEGORY",
            "pack format": "PACKAGING",
            "container": "PACKAGING",
            "fulfillment route": "SALES_CHANNEL",
            "go to market": "SALES_CHANNEL",
            "customer happiness": "CUSTOMER_RATING",
            "star rating": "CUSTOMER_RATING",
            "geographic territory": "MARKET_REGION",
            "units dispatched": "UNITS_SOLD",
        },
        "formulas": {
            "gross_profit_usd": {
                "description": "Dollar gross profit per line item",
                "formula": "NET_SALES_USD * (GROSS_MARGIN_PCT / 100.0)",
                "target_type": "measure",
            },
            "average_selling_price": {
                "description": "Realized price per unit",
                "formula": "NET_SALES_USD / UNITS_SOLD",
                "target_type": "measure",
            }
        }
    }
}


def _get_glossary_file(client_id: str) -> Path:
    return GLOSSARY_DIR / f"{client_id}_glossary.json"


def load_client_glossary(client_id: str) -> Dict[str, Any]:
    """Loads client business glossary from disk, initializing from defaults if missing."""
    file_path = _get_glossary_file(client_id)
    if not file_path.exists():
        # Initialize default
        default_data = DEFAULT_GLOSSARY.get(client_id, {
            "client_name": client_id,
            "aliases": {},
            "formulas": {}
        })
        save_client_glossary(client_id, default_data)
        return default_data

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_GLOSSARY.get(client_id, {"aliases": {}, "formulas": {}})


def save_client_glossary(client_id: str, data: Dict[str, Any]) -> bool:
    """Saves updated glossary to persistent disk."""
    file_path = _get_glossary_file(client_id)
    try:
        tmp_path = file_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(file_path)
        return True
    except Exception as e:
        print(f"[GLOSSARY SAVE ERROR] {e}")
        return False


def add_glossary_term(
    client_id: str,
    term: str,
    target_column: str,
    term_type: str = "alias",
    description: Optional[str] = None,
    formula: Optional[str] = None
) -> Tuple[bool, str]:
    """Registers or updates a business term or custom formula."""
    term_clean = term.strip().lower()
    target_clean = target_column.strip()

    if not term_clean or not target_clean:
        return False, "Term and target column cannot be empty."

    glossary = load_client_glossary(client_id)

    if term_type == "formula":
        glossary.setdefault("formulas", {})[term_clean] = {
            "description": description or f"Custom calculated formula for {term_clean}",
            "formula": formula or target_clean,
            "target_type": "formula"
        }
    else:
        glossary.setdefault("aliases", {})[term_clean] = target_clean

    success = save_client_glossary(client_id, glossary)
    return success, "Glossary updated successfully." if success else "Failed to persist glossary."


def delete_glossary_term(client_id: str, term: str) -> Tuple[bool, str]:
    """Removes a custom business term from the active glossary."""
    term_clean = term.strip().lower()
    glossary = load_client_glossary(client_id)

    removed = False
    if "aliases" in glossary and term_clean in glossary["aliases"]:
        del glossary["aliases"][term_clean]
        removed = True

    if "formulas" in glossary and term_clean in glossary["formulas"]:
        del glossary["formulas"][term_clean]
        removed = True

    if not removed:
        return False, f"Term '{term_clean}' not found in active glossary."

    success = save_client_glossary(client_id, glossary)
    return success, "Term removed successfully." if success else "Failed to save changes."


def resolve_glossary_term(term: str, client_id: str) -> Optional[str]:
    """Looks up term in client's custom jargon dictionary."""
    glossary = load_client_glossary(client_id)
    aliases = glossary.get("aliases", {})
    t_clean = term.strip().lower()
    return aliases.get(t_clean)


def get_llm_glossary_prompt(client_id: str) -> str:
    """Formats active business glossary into LLM system prompt instructions."""
    glossary = load_client_glossary(client_id)
    aliases = glossary.get("aliases", {})
    formulas = glossary.get("formulas", {})

    if not aliases and not formulas:
        return ""

    lines = ["ENTERPRISE BUSINESS GLOSSARY & JARGON MAPPINGS:"]
    if aliases:
        lines.append("Recognize these company-specific synonyms and map them strictly to the designated columns:")
        for alias, target in aliases.items():
            lines.append(f'  - "{alias}" -> Map to column: {target}')

    if formulas:
        lines.append("Recognize these calculated enterprise business metrics and their definitions:")
        for name, info in formulas.items():
            lines.append(f'  - "{name}": {info.get("description", "")} (Formula: {info.get("formula", "")})')

    return "\n".join(lines)
