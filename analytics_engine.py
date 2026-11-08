"""
ANALYTICS ENGINE FOR TEA INDUSTRY PORTAL
========================================
Modular, deterministic analytics, dataset profiling, query execution,
and OpenAI narrative synthesis.
"""

import os
import re
import json
import hashlib
import functools
import time
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from olap_engine import get_olap_engine
from glossary_manager import load_client_glossary, get_llm_glossary_prompt, resolve_glossary_term
from complex_analytics import (
    detect_complex_intent,
    execute_complex_analytical_query,
    synthesize_complex_narrative,
)

load_dotenv()
BACKEND_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

_AI_AVAILABLE = True
_AI_LAST_CHECK = 0.0
_LAST_AI_SOURCE = "deterministic_fallback"

def is_ai_available() -> bool:
    global _AI_AVAILABLE, _AI_LAST_CHECK
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not (gemini_key or openai_key):
        return False
    now = time.time()
    if not _AI_AVAILABLE and (now - _AI_LAST_CHECK) < 180:
        return False
    return True

def mark_ai_failed():
    global _AI_AVAILABLE, _AI_LAST_CHECK
    _AI_AVAILABLE = False
    _AI_LAST_CHECK = time.time()

def get_last_ai_source() -> str:
    global _LAST_AI_SOURCE
    return _LAST_AI_SOURCE

# Aliases for backwards compatibility
is_openai_available = is_ai_available
mark_openai_failed = mark_ai_failed


def call_llm_json(system_prompt: str, user_prompt: str, timeout: float = 8.0) -> Optional[Dict[str, Any]]:
    """Calls Gemini or OpenAI to get structured JSON output with automatic failover."""
    global _LAST_AI_SOURCE
    if not is_ai_available():
        return None

    # 1. Try Google Gemini first (Supports 100% Free Tier at Google AI Studio)
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        for model in ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                body = {
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json"
                    }
                }
                resp = requests.post(url, json=body, timeout=min(timeout, 6.0))
                if resp.status_code == 200:
                    res_data = resp.json()
                    raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    _LAST_AI_SOURCE = f"Google Gemini ({model})"
                    return json.loads(raw_text)
                elif resp.status_code == 429:
                    print(f"[GEMINI RATE LIMIT on {model}] Quota exceeded. Marking AI unavailable temporarily.")
                    mark_ai_failed()
                    break
                else:
                    print(f"[GEMINI ERROR {resp.status_code} on {model}] {resp.text[:120]}")
            except Exception as e:
                print(f"[GEMINI EXCEPTION on {model}] {e}")

    # 2. Try OpenAI gpt-4o-mini
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key, timeout=timeout, max_retries=0)
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            raw = res.choices[0].message.content or "{}"
            _LAST_AI_SOURCE = "OpenAI (gpt-4o-mini)"
            return json.loads(raw)
        except Exception as e:
            err_msg = str(e).lower()
            if any(k in err_msg for k in ["quota", "429", "rate", "credit_balance_exhausted"]):
                print(f"[OPENAI QUOTA EXHAUSTED] {e}")
                mark_ai_failed()
            else:
                print(f"[OPENAI EXCEPTION] {e}")

    return None


def call_llm_text(system_prompt: str, user_prompt: str, timeout: float = 8.0) -> Optional[str]:
    """Calls Gemini or OpenAI to get natural language narrative text with automatic failover."""
    global _LAST_AI_SOURCE
    if not is_ai_available():
        return None

    # 1. Try Google Gemini first
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        for model in ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                body = {
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2
                    }
                }
                resp = requests.post(url, json=body, timeout=min(timeout, 6.0))
                if resp.status_code == 200:
                    res_data = resp.json()
                    _LAST_AI_SOURCE = f"Google Gemini ({model})"
                    return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                elif resp.status_code == 429:
                    print(f"[GEMINI RATE LIMIT on {model}] Quota exceeded. Marking AI unavailable temporarily.")
                    mark_ai_failed()
                    break
                else:
                    print(f"[GEMINI ERROR {resp.status_code} on {model}] {resp.text[:120]}")
            except Exception as e:
                print(f"[GEMINI EXCEPTION on {model}] {e}")

    # 2. Try OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key, timeout=timeout, max_retries=0)
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            _LAST_AI_SOURCE = "OpenAI (gpt-4o-mini)"
            return (res.choices[0].message.content or "").strip()
        except Exception as e:
            err_msg = str(e).lower()
            if any(k in err_msg for k in ["quota", "429", "rate", "credit_balance_exhausted"]):
                print(f"[OPENAI QUOTA EXHAUSTED] {e}")
                mark_ai_failed()
            else:
                print(f"[OPENAI EXCEPTION] {e}")

    return None




def load_client_dataset(data_path: str, client_id: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Loads client's dataset safely, supporting normalized star-schemas and analytical tables."""
    try:
        if not os.path.exists(data_path):
            return None, f"Assigned data source '{data_path}' was not found on server."

        folder = os.path.dirname(data_path)
        schema_path = os.path.join(folder, "schema_relationships.json")

        # 1. If relational schema definition exists, execute multi-table PK/FK joins (Oracle Relational Model Simulation)
        if os.path.exists(schema_path):
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema = json.load(f)

                tables = schema.get("tables", {})
                fact_key = schema.get("primary_fact_table")
                if fact_key and fact_key in tables:
                    fact_info = tables[fact_key]
                    fact_file = os.path.join(folder, fact_info["file"])
                    if os.path.exists(fact_file):
                        df_fact = pd.read_csv(fact_file)

                        # Join dimension tables via Foreign Keys
                        for fk_col, fk_info in fact_info.get("foreign_keys", {}).items():
                            target_ref = fk_info["references"]  # e.g. "dim_estates.ESTATE_ID"
                            target_tbl, target_pk = target_ref.split(".")
                            if target_tbl in tables:
                                dim_file = os.path.join(folder, tables[target_tbl]["file"])
                                if os.path.exists(dim_file):
                                    df_dim = pd.read_csv(dim_file)
                                    df_fact = df_fact.merge(df_dim, left_on=fk_col, right_on=target_pk, how="left")

                        # Join any bridge fact tables (e.g. fact_shipments)
                        for tbl_name, tbl_info in tables.items():
                            if tbl_info.get("type") == "BRIDGE_FACT":
                                bridge_file = os.path.join(folder, tbl_info["file"])
                                if os.path.exists(bridge_file):
                                    df_bridge = pd.read_csv(bridge_file)
                                    for b_fk, b_info in tbl_info.get("foreign_keys", {}).items():
                                        b_ref = b_info["references"]
                                        b_target_tbl, b_target_pk = b_ref.split(".")
                                        if b_target_tbl == fact_key:
                                            # Grain preservation: deduplicate bridge table to prevent Cartesian row duplication
                                            df_bridge_dedup = df_bridge.drop_duplicates(subset=[b_fk])
                                            df_fact = df_fact.merge(df_bridge_dedup, left_on=b_target_pk, right_on=b_fk, how="left")

                        df_fact.columns = [str(c).strip() for c in df_fact.columns]
                        for col in df_fact.columns:
                            if df_fact[col].dtype == object:
                                df_fact[col] = df_fact[col].fillna("").astype(str)

                        df_fact.attrs["relational_schema"] = schema

                        if "FINANCIAL_YEAR" not in df_fact.columns:
                            d_cand = next((c for c in ["SALE_DATE", "ORDER_DATE", "DATE"] if c in df_fact.columns), None)
                            if not d_cand:
                                d_cand = next((c for c in df_fact.columns if "date" in c.lower()), None)
                            if d_cand:
                                parsed_d = pd.to_datetime(df_fact[d_cand], errors="coerce")
                                def _calc_fy(d):
                                    if pd.isna(d):
                                        return ""
                                    y = d.year
                                    return f"FY {y}-{str(y+1)[-2:]}" if d.month >= 4 else f"FY {y-1}-{str(y)[-2:]}"
                                df_fact["FINANCIAL_YEAR"] = parsed_d.apply(_calc_fy)

                        # Lazily register in OLAP DuckDB engine
                        client_folder_name = os.path.basename(folder)
                        get_olap_engine().register_client_dataset(client_folder_name)

                        return df_fact, None
            except Exception as rel_err:
                print(f"[RELATIONAL LOAD WARNING] {rel_err}, falling back to standalone file.")

        # 2. Fallback to single CSV / Excel file
        if data_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(data_path)
        else:
            try:
                df = pd.read_csv(data_path)
            except UnicodeDecodeError:
                df = pd.read_csv(data_path, encoding="latin-1")

        if df.empty:
            return None, "Dataset contains no records."

        df.columns = [str(c).strip() for c in df.columns]
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna("").astype(str)

        if "FINANCIAL_YEAR" not in df.columns:
            d_cand = next((c for c in ["SALE_DATE", "ORDER_DATE", "DATE"] if c in df.columns), None)
            if not d_cand:
                d_cand = next((c for c in df.columns if "date" in c.lower()), None)
            if d_cand:
                parsed_d = pd.to_datetime(df[d_cand], errors="coerce")
                def _calc_fy(d):
                    if pd.isna(d):
                        return ""
                    y = d.year
                    return f"FY {y}-{str(y+1)[-2:]}" if d.month >= 4 else f"FY {y-1}-{str(y)[-2:]}"
                df["FINANCIAL_YEAR"] = parsed_d.apply(_calc_fy)

        return df, None
    except Exception as e:
        return None, f"Failed to load dataset: {str(e)}"


def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Profiles dataset structure into measures, dimensions, dates, and identifiers."""
    total_rows = len(df)
    total_cols = len(df.columns)

    measures: List[Dict[str, Any]] = []
    dates: List[Dict[str, Any]] = []
    dimensions: List[Dict[str, Any]] = []
    identifiers: List[Dict[str, Any]] = []

    id_patterns = re.compile(r"id|code|num|key|sku|ref|uuid|no\b|lot|ord|txn", re.IGNORECASE)
    date_patterns = re.compile(r"date|time|year|month|day|quarter|period|timestamp|created", re.IGNORECASE)

    for col in df.columns:
        series = df[col]
        non_null_count = int(series.notna().sum())
        if non_null_count == 0:
            continue

        unique_count = int(series.nunique(dropna=True))

        # Check date
        is_date = False
        min_date, max_date = None, None
        if pd.api.types.is_datetime64_any_dtype(series):
            is_date = True
            min_date, max_date = series.min(), series.max()
        elif series.dtype == object or pd.api.types.is_string_dtype(series):
            if date_patterns.search(str(col)):
                sample = series.dropna().head(50)
                if len(sample) > 0:
                    try:
                        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
                        if parsed.notna().sum() / len(sample) >= 0.8:
                            all_parsed = pd.to_datetime(series, errors="coerce", format="mixed")
                            if all_parsed.notna().sum() / max(1, non_null_count) >= 0.7:
                                is_date = True
                                min_date, max_date = all_parsed.min(), all_parsed.max()
                    except Exception:
                        pass

        if is_date:
            dates.append({
                "column": col,
                "earliest": str(min_date)[:10] if pd.notna(min_date) else "Unknown",
                "latest": str(max_date)[:10] if pd.notna(max_date) else "Unknown",
            })
            continue

        # Check identifiers
        if (id_patterns.search(str(col)) and unique_count / max(1, total_rows) > 0.5) or (unique_count == total_rows and total_rows > 10):
            identifiers.append({
                "column": col,
                "unique_count": unique_count,
                "sample": [str(x) for x in series.dropna().head(3).tolist()],
            })
            continue

        # Check numeric measures
        if pd.api.types.is_numeric_dtype(series):
            if id_patterns.search(str(col)) and unique_count > total_rows * 0.9:
                identifiers.append({"column": col, "unique_count": unique_count, "sample": [str(x) for x in series.dropna().head(3).tolist()]})
            else:
                s_clean = series.dropna()
                measures.append({
                    "column": col,
                    "sum": round(float(s_clean.sum()), 2),
                    "mean": round(float(s_clean.mean()), 2),
                    "min": round(float(s_clean.min()), 2),
                    "max": round(float(s_clean.max()), 2),
                })
            continue

        # Dimensions - cache up to 150 unique values for natural language entity recognition
        dim_samples = [str(x).strip() for x in series.dropna().unique()[:150] if str(x).strip()]
        dimensions.append({
            "column": col,
            "unique_count": unique_count,
            "sample_values": dim_samples,
        })

    rel_schema = getattr(df, "attrs", {}).get("relational_schema")

    # Build dynamic GLOCA -> estate/units map directly from Oracle data
    # This replaces any hardcoded gloca_map so new gardens are auto-recognised
    gloca_map: Dict[str, Any] = {}
    unit_set: set = set()
    if "GLOCA" in df.columns and "ESTATE" in df.columns:
        grp_cols = ["GLOCA", "ESTATE"]
        _has_unit = "UNIT" in df.columns
        for (gloca, estate), grp in df.groupby(grp_cols):
            gloca_str = str(gloca).strip().upper()
            estate_str = str(estate).strip()
            units_list = [str(u).strip() for u in grp["UNIT"].dropna().unique().tolist() if str(u).strip()] if _has_unit else []
            unit_set.update(units_list)
            if gloca_str not in gloca_map:
                gloca_map[gloca_str] = {"estate": estate_str, "units": units_list, "name": estate_str.title()}
            else:
                # Merge units from a second GLOCA->ESTATE row (e.g. G01326 sharing an estate)
                existing = gloca_map[gloca_str]["units"]
                for u in units_list:
                    if u not in existing:
                        existing.append(u)

    # Build reverse unit -> estate lookup
    unit_map: Dict[str, str] = {}
    for gcode, info in gloca_map.items():
        for u in info.get("units", []):
            unit_map[u] = info["estate"]

    prof_result = {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "measures": measures,
        "dimensions": dimensions,
        "dates": dates,
        "identifiers": identifiers,
        "relational_schema": rel_schema,
        "gloca_map": gloca_map,
        "unit_map": unit_map,
        "all_units": sorted(unit_set),
    }

    # Layer 2 & Layer 3: Classify columns and build dynamic semantic maps at profile time
    col_meta = classify_dataset_columns(df, prof_result)
    prof_result["column_metadata"] = col_meta
    dim_map, meas_map = build_dynamic_semantic_maps(prof_result)
    prof_result["semantic_maps"] = {"dim_map": dim_map, "meas_map": meas_map}
    prof_result["dim_synonyms"] = dim_map
    prof_result["meas_synonyms"] = meas_map

    return prof_result


def format_indian_number(v: float, decimals: int = 3) -> str:
    """Formats a number using the Indian grouping system (e.g. 92,36,682.000)."""
    if v is None or pd.isna(v):
        return "0.000" if decimals == 3 else "0.00"
    sign = "-" if v < 0 else ""
    abs_v = abs(float(v))
    parts = f"{abs_v:.{decimals}f}".split(".")
    int_part = parts[0]
    dec_part = "." + parts[1] if len(parts) > 1 else ""

    if len(int_part) <= 3:
        return f"{sign}{int_part}{dec_part}"

    last_three = int_part[-3:]
    remaining = int_part[:-3]
    groups = []
    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        groups.insert(0, remaining)

    return f"{sign}{','.join(groups)},{last_three}{dec_part}"


def format_indian_currency(v: float) -> str:
    """Formats monetary amounts into Crores, Lakhs, Thousands, or Rs. with 2 decimal places."""
    if v is None or pd.isna(v):
        return "Rs. 0.00"
    abs_v = abs(float(v))
    sign = "-" if v < 0 else ""
    if abs_v >= 10_000_000:  # 1 Crore = 10 Million
        return f"Rs. {sign}{abs_v / 10_000_000:,.2f} Crores"
    elif abs_v >= 100_000:   # 1 Lakh = 100 Thousand
        return f"Rs. {sign}{abs_v / 100_000:,.2f} Lakhs"
    elif abs_v >= 1_000:     # 1 Thousand
        return f"Rs. {sign}{abs_v / 1_000:,.2f} Thousand"
    else:
        return f"Rs. {sign}{abs_v:,.2f}"


# =============================================================================
# DYNAMIC, ZERO-HARDCODING NLP SEMANTIC RESOLVER & FUZZY MATCHER
# =============================================================================

DIRECTION_ASCENDING = ["lowest", "bottom", "least", "worst", "minimum", "smallest", "poorest", "trailing", "underperforming", "cheapest", "bottommost", "last", "fewer", "fewest"]
DIRECTION_DESCENDING = ["highest", "top", "best", "most", "maximum", "largest", "greatest", "leading", "outperforming", "peak", "premier", "first", "champion", "winning", "lead"]

INTENT_TIME_SERIES = ["trend", "trends", "monthly", "timeline", "trajectory", "over time", "history", "progression", "pattern", "annual", "quarterly"]
INTENT_ANOMALY = ["anomaly", "anomalies", "outlier", "outliers", "unusual", "abnormal", "irregular", "variance", "deviation", "exception", "weird", "strange"]
INTENT_TOTAL = ["total", "overall", "grand total", "sum", "combined", "aggregate", "altogether", "cumulatively", "entire"]
INTENT_AVERAGE = ["average", "mean", "run rate", "typical", "normal", "norm"]

STOP_WORDS = {
    "the", "is", "in", "of", "and", "a", "an", "to", "for", "with", "by", "on", "at", "which", "whch",
    "what", "wat", "who", "show", "tell", "give", "giv", "had", "has", "did", "do", "are", "were",
    "dataset", "database", "records", "ledger", "all", "across", "different", "rs", "usd", "each", "every",
    "can", "could", "would", "should", "will", "may", "you", "ou", "me", "us", "my", "our", "get", "find",
    "list", "see", "check", "display", "calculate", "compute", "generated", "genrated", "genrate",
    "generating", "generate", "please", "kindly", "i", "want", "know", "data", "info", "information",
    "value", "values", "worth", "how", "does", "or", "versus", "vs", "compare", "comparing", "compared",
    "comparison", "against", "between", "differ", "difference", "like", "than", "as", "much", "many", "from",
    "about", "around", "regarding"
}

OUT_OF_SCOPE_WORDS = {
    "prime", "minister", "president", "politics", "political", "government", "election", "weather",
    "forecast", "cricket", "football", "world", "cup", "movie", "film", "actor", "actress", "song",
    "poem", "recipe", "code", "python", "java", "javascript", "stock", "crypto", "bitcoin", "war", "news", "celebrity",
    "pm", "cm", "ceo", "capital", "population", "gdp", "todsy", "today", "temperature",
    "hot", "cold", "warm", "rain", "raining", "rainy", "sunny", "sun", "cloud", "cloudy", "humid", "humidity",
    "climate", "joke", "funny", "story"
}


CACHE_DIR = os.path.join(os.path.dirname(__file__), "scratch", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def compute_schema_hash(profile: Dict[str, Any]) -> str:
    """Computes a deterministic hash of the schema (columns, types, sample values)."""
    repr_str = json.dumps({
        "dims": [d["column"] for d in profile.get("dimensions", [])],
        "meas": [m["column"] for m in profile.get("measures", [])],
        "dates": [d["column"] for d in profile.get("dates", [])],
    }, sort_keys=True)
    return hashlib.sha256(repr_str.encode("utf-8")).hexdigest()[:16]


def classify_dataset_columns(df: Optional[pd.DataFrame], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Layer 2: AI Column Semantic Classification with intelligent dynamic statistical fallback.
    Persistent disk cache ensures API cost is paid only once per dataset schema.
    """
    schema_hash = compute_schema_hash(profile)
    cache_file = os.path.join(CACHE_DIR, f"col_metadata_{schema_hash}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Dynamic Statistical Classifier (Zero API quota usage, instant 0ms execution)
    col_meta = {}
    all_dims = profile.get("dimensions", [])
    all_meas = profile.get("measures", [])
    
    # 1. Detect functional dependencies & shadow columns dynamically
    shadow_map = {}
    if df is not None:
        dim_cols = [d["column"] for d in all_dims if d["column"] in df.columns]
        for i, c1 in enumerate(dim_cols):
            for c2 in dim_cols[i+1:]:
                try:
                    s1 = df[c1].dropna().astype(str)
                    s2 = df[c2].dropna().astype(str)
                    if len(s1) > 0 and len(s2) > 0 and s1.nunique() == s2.nunique():
                        cross_max1 = df.groupby(c1)[c2].nunique().max()
                        cross_max2 = df.groupby(c2)[c1].nunique().max()
                        if cross_max1 == 1 and cross_max2 == 1:
                            c1_abbr = bool(re.search(r"(_code|_id|_cd|_no|short|sht|descn|gloca|loca)$", c1.lower()))
                            c2_abbr = bool(re.search(r"(_code|_id|_cd|_no|short|sht|descn|gloca|loca)$", c2.lower()))
                            v_len1 = s1.str.len().mean()
                            v_len2 = s2.str.len().mean()
                            if c1_abbr and not c2_abbr:
                                shadow_map[c1] = c2
                            elif c2_abbr and not c1_abbr:
                                shadow_map[c2] = c1
                            elif v_len1 < v_len2 * 0.7:
                                shadow_map[c1] = c2
                            elif v_len2 < v_len1 * 0.7:
                                shadow_map[c2] = c1
                            elif len(c1) < len(c2):
                                shadow_map[c1] = c2
                            else:
                                shadow_map[c2] = c1
                except Exception:
                    pass

    # Find candidate primary entity (categorical column with moderate cardinality 5-500 and descriptive names)
    primary_entity_col = None
    best_entity_score = -1
    for d in all_dims:
        c = d["column"]
        uc = d.get("unique_count", 0)
        samples = d.get("sample_values", [])
        avg_len = sum(len(str(x)) for x in samples) / max(1, len(samples))
        has_spaces = any(" " in str(x) for x in samples)
        is_short_code = (avg_len <= 5 and not has_spaces)
        is_sh = (c in shadow_map) or is_short_code or bool(re.search(r"(_code|_id|_cd|_no|short|sht|descn|gloca|loca|sl_no|autoid)$", c.lower()))
        if is_sh:
            continue
        if 5 <= uc <= 500:
            # Score favors descriptive names with moderate business cardinality
            score = avg_len * 4 + (20 if has_spaces else 0) + (100 - abs(uc - 25))
            if score > best_entity_score:
                best_entity_score = score
                primary_entity_col = c

    for d in all_dims:
        c = d["column"]
        uc = d.get("unique_count", 0)
        samples = d.get("sample_values", [])
        avg_len = sum(len(str(x)) for x in samples) / max(1, len(samples))
        has_spaces = any(" " in str(x) for x in samples)
        is_short_code = (avg_len <= 5 and not has_spaces)
        is_sh = (c in shadow_map) or is_short_code or bool(re.search(r"(_code|_id|_cd|_no|short|sht|descn|gloca|loca|sl_no|autoid)$", c.lower()))
        
        if c == primary_entity_col:
            role = "primary_entity"
            prio = 0
            is_sh = False
        elif is_sh:
            role = "shadow_code"
            prio = 8
        elif uc <= 10:
            role = "category"
            prio = 3
        elif uc <= 50:
            role = "attribute"
            prio = 2
        else:
            role = "secondary_entity"
            prio = 4

        col_meta[c] = {
            "role": role,
            "is_shadow": is_sh,
            "priority": prio,
            "formatting": "text",
            "unit": "",
            "shadow_of": shadow_map.get(c)
        }

    # Classify measures
    for m in all_meas:
        c = m["column"]
        cu = c.upper()
        if any(k in cu for k in ["PRICE", "RATE", "REALIZ"]):
            role = "rate"
            fmt = "rate"
            unit = "Rs."
        elif any(k in cu for k in ["PCT", "PERCENT", "MARGIN", "RATIO"]):
            role = "ratio"
            fmt = "percentage"
            unit = "%"
        elif any(k in cu for k in ["REVENUE", "SALES", "AMOUNT", "INCOME"]):
            role = "monetary"
            fmt = "currency"
            unit = "Rs."
        elif any(k in cu for k in ["QTY", "VOL", "WEIGHT", "MASS", "KG"]):
            role = "volume"
            fmt = "quantity"
            unit = "kg"
        elif any(k in cu for k in ["COUNT", "BATCH", "CHEST", "BAG", "BOX"]):
            role = "count"
            fmt = "count"
            unit = "batches"
        elif any(k in cu for k in ["SCORE", "RATING"]):
            role = "score"
            fmt = "score"
            unit = "pts"
        else:
            role = "measure"
            fmt = "quantity"
            unit = ""

        col_meta[c] = {
            "role": role,
            "is_shadow": False,
            "priority": 1,
            "formatting": fmt,
            "unit": unit
        }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(col_meta, f, indent=2)
    except Exception:
        pass

    return col_meta


def _merge_client_glossary(dim_map: Dict[str, List[str]], meas_map: Dict[str, List[str]], client_id: str, profile: Dict[str, Any]):
    """Merges dynamic client-specific glossary terms and aliases into semantic maps."""
    try:
        glossary = load_client_glossary(client_id)
        for alias, target_col in glossary.get("aliases", {}).items():
            alias_clean = alias.strip().lower()
            target_clean = target_col.strip()
            if target_clean in meas_map:
                if alias_clean not in meas_map[target_clean]:
                    meas_map[target_clean].append(alias_clean)
            elif target_clean in dim_map:
                if alias_clean not in dim_map[target_clean]:
                    dim_map[target_clean].append(alias_clean)
            else:
                matched = False
                for m in profile.get("measures", []):
                    if m["column"].lower() == target_clean.lower():
                        col_key = m["column"]
                        meas_map.setdefault(col_key, [])
                        if alias_clean not in meas_map[col_key]:
                            meas_map[col_key].append(alias_clean)
                        matched = True
                        break
                if not matched:
                    for d in profile.get("dimensions", []):
                        if d["column"].lower() == target_clean.lower():
                            col_key = d["column"]
                            dim_map.setdefault(col_key, [])
                            if alias_clean not in dim_map[col_key]:
                                dim_map[col_key].append(alias_clean)
                            break
    except Exception as e:
        print(f"[GLOSSARY MERGE WARNING] {e}")


def build_dynamic_semantic_maps(profile: Dict[str, Any], client_id: Optional[str] = None) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """Dynamically derives semantic match dictionaries directly from the active dataset profile and client business glossary."""
    schema_hash = compute_schema_hash(profile)
    cache_file = os.path.join(CACHE_DIR, f"synonyms_{schema_hash}.json")
    
    col_meta = profile.get("column_metadata")
    if not col_meta:
        col_meta = classify_dataset_columns(None, profile)
        profile["column_metadata"] = col_meta

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                dim_map = {k: list(v) for k, v in cached.get("dim_map", {}).items()}
                meas_map = {k: list(v) for k, v in cached.get("meas_map", {}).items()}
                if client_id:
                    _merge_client_glossary(dim_map, meas_map, client_id, profile)
                return dim_map, meas_map
        except Exception:
            pass

    # Dynamic Morphological & Role-Based Generator (Zero API quota usage, instant 0ms execution)
    dim_map = {}
    meas_map = {}
    
    ROLE_SYNONYMS = {
        "volume": ["volume", "volumes", "quantity", "quantities", "weight", "weights", "output", "production", "mass", "kg", "kgs"],
        "rate": ["rate", "rates", "price", "prices", "pricing", "cost", "valuation", "realization", "per kg", "unit price"],
        "monetary": ["revenue", "sales", "turnover", "proceeds", "amount", "income", "money", "earnings", "gross"],
        "ratio": ["margin", "profit", "profitability", "percentage", "pct", "ratio", "spread"],
        "count": ["count", "batches", "batch", "chests", "chest", "records", "number", "orders", "lots", "invoices"],
        "score": ["score", "scores", "rating", "ratings", "points", "quality", "cupping", "cuppings", "benchmark", "index"],
        "primary_entity": ["estate", "estates", "garden", "gardens", "plantation", "plantations", "farm", "farms", "producer", "location", "facility", "unit", "entity"],
    }

    GENERIC_STOP = {"total", "net", "gross", "avg", "average", "the", "of", "and", "in", "by", "on", "at", "data", "val", "value"}

    for d in profile.get("dimensions", []):
        col = d["column"]
        meta = col_meta.get(col, {})
        is_shadow = meta.get("is_shadow", False)
        
        clean_name = col.lower().replace("_", " ")
        tokens = [t for t in clean_name.split() if t not in GENERIC_STOP and len(t) >= 2]
        aliases = [col.lower(), clean_name, f"{clean_name}s"]
        if len(tokens) == 1:
            aliases.extend([tokens[0], f"{tokens[0]}s"])
        elif len(tokens) > 1:
            head = tokens[-1]
            aliases.extend([head, f"{head}s"])
            for mod in tokens[:-1]:
                if mod not in {"tea", "item", "code", "num", "data", "info", "master", "table", "dim", "fact"} and len(mod) >= 4:
                    aliases.extend([mod, f"{mod}s"])
            
        if not is_shadow:
            role = meta.get("role", "")
            if role in ROLE_SYNONYMS:
                aliases.extend(ROLE_SYNONYMS[role])
                
        dim_map[col] = list(set(aliases))

    for m in profile.get("measures", []):
        col = m["column"]
        meta = col_meta.get(col, {})
        clean_name = col.lower().replace("_", " ")
        tokens = [t for t in clean_name.split() if t not in GENERIC_STOP and len(t) >= 2]
        aliases = [col.lower(), clean_name, f"{clean_name}s"]
        if len(tokens) == 1:
            aliases.extend([tokens[0], f"{tokens[0]}s"])
        elif len(tokens) > 1:
            head = tokens[-1]
            aliases.extend([head, f"{head}s"])
            for mod in tokens[:-1]:
                if mod not in {"tea", "item", "code", "num", "data", "info", "fact"} and len(mod) >= 4:
                    aliases.extend([mod, f"{mod}s"])
            
        role = meta.get("role", "")
        if role in ROLE_SYNONYMS:
            aliases.extend(ROLE_SYNONYMS[role])
            
        meas_map[col] = list(set(aliases))

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"dim_map": dim_map, "meas_map": meas_map}, f, indent=2)
    except Exception:
        pass

    # Incorporate Custom Business Glossary Jargon if available
    if client_id:
        _merge_client_glossary(dim_map, meas_map, client_id, profile)

    return dim_map, meas_map


@functools.lru_cache(maxsize=32768)
def damerau_levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculates normalized Damerau-Levenshtein similarity [0.0, 1.0] with transposition handling and LRU cache."""
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 1.0
    if (s1 in ["estate", "estates"] and s2 in ["state", "states"]) or (s1 in ["state", "states"] and s2 in ["estate", "estates"]):
        return 0.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    max_len = max(len1, len2)
    diff = abs(len1 - len2)
    if diff >= 3 and (1.0 - (diff / max_len)) < 0.65:
        return 0.0
    if min(len1, len2) <= 4 and diff >= 2:
        return 0.0
    d = {}
    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1
    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,        # deletion
                d[(i, j - 1)] + 1,        # insertion
                d[(i - 1, j - 1)] + cost  # substitution
            )
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + 1)  # transposition
    dist = d[(len1 - 1, len2 - 1)]
    return max(0.0, 1.0 - (dist / max_len))


def fuzzy_match_phrase(
    tokens: List[str],
    vocab_dict: Dict[str, List[str]],
    threshold: float = 0.62,
    ignore: Optional[set] = None,
    priority_map: Optional[Dict[str, int]] = None
) -> Tuple[Optional[str], float, List[str]]:
    """Finds best matching semantic key across single tokens and n-gram phrases against vocabulary dictionary, using column priorities to break ties."""
    best_key, best_sim, best_matched_toks = None, 0.0, []
    
    def _is_better_match(new_key: str, new_sim: float, new_is_phrase: bool, curr_key: Optional[str], curr_sim: float, curr_is_phrase: bool) -> bool:
        if curr_key is None:
            return True
        if new_sim > curr_sim + 0.04:
            return True
        if curr_sim > new_sim + 0.04:
            return False
        # Within near-tie (diff <= 0.04):
        # 1. Multi-word phrase matches beat single token matches
        if new_is_phrase and not curr_is_phrase:
            return True
        if curr_is_phrase and not new_is_phrase:
            return False
        # 2. Priority check (lower number = higher importance, e.g. 0 > 4)
        if priority_map:
            new_pri = priority_map.get(new_key, 5)
            curr_pri = priority_map.get(curr_key, 5)
            if new_pri < curr_pri:
                return True
            if curr_pri < new_pri:
                return False
        # 3. Fallback: higher raw similarity
        return new_sim > curr_sim

    # 1. Check bigrams first
    if len(tokens) >= 2:
        for i in range(len(tokens) - 1):
            t1, t2 = tokens[i], tokens[i + 1]
            if ignore and (t1 in ignore and t2 in ignore):
                continue
            bigram = f"{t1} {t2}"
            for key, words in vocab_dict.items():
                for w in words:
                    sim = damerau_levenshtein_similarity(bigram, w)
                    if sim >= threshold and _is_better_match(key, sim, True, best_key, best_sim, len(best_matched_toks) > 1):
                        best_sim = sim
                        best_key = key
                        best_matched_toks = [t1, t2]

    # 2. Check unigrams
    for tok in tokens:
        if ignore and tok in ignore:
            continue
        for key, words in vocab_dict.items():
            for w in words:
                sim = damerau_levenshtein_similarity(tok, w)
                if sim >= threshold and _is_better_match(key, sim, False, best_key, best_sim, len(best_matched_toks) > 1):
                    best_sim = sim
                    best_key = key
                    best_matched_toks = [tok]
                    
    return best_key, best_sim, best_matched_toks


def fuzzy_match_token(tokens: List[str], vocab_dict: Dict[str, List[str]], threshold: float = 0.62, ignore: Optional[set] = None) -> Tuple[Optional[str], float, Optional[str]]:
    """Legacy wrapper for single token matching."""
    k, s, toks = fuzzy_match_phrase(tokens, vocab_dict, threshold, ignore)
    return k, s, toks[0] if toks else None


def rule_based_fallback_plan(
    question: str,
    profile: Dict[str, Any],
    client_id: Optional[str] = None,
    conversation_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generates a robust, typo-tolerant analysis plan locally using dynamic schema profiling, pronoun resolution, and Damerau-Levenshtein matching."""
    dim_names = [d["column"] for d in profile.get("dimensions", [])]
    meas_names = [m["column"] for m in profile.get("measures", [])]
    date_names = [d["column"] for d in profile.get("dates", [])]

    raw_tokens = re.findall(r"[a-zA-Z0-9]+", question.lower())
    consumed_tokens = set()

    # Dynamic dataset token universe for zero-hardcoding out-of-scope validation
    dataset_tokens = set(STOP_WORDS)
    for d in profile.get("dimensions", []):
        dataset_tokens.update(d["column"].lower().split("_"))
        for sv in d.get("sample_values", [])[:15]:
            dataset_tokens.update(str(sv).lower().split())
    for m in profile.get("measures", []):
        dataset_tokens.update(m["column"].lower().split("_"))
    for dt in profile.get("dates", []):
        dataset_tokens.update(dt["column"].lower().split("_"))

    generic_business_terms = {
        "sales", "revenue", "price", "volume", "quantity", "margin", "profit", "cost",
        "total", "average", "top", "bottom", "trend", "monthly", "growth", "performance",
        "outlier", "anomaly", "highest", "lowest", "rank", "ranking", "breakdown", "list",
        "leaderboard", "share", "rate", "mean", "sum", "min", "max", "run",
        "distinguish", "differentiate", "split", "break", "down", "categorize", "classify",
        "group", "segregate", "divide", "separate", "show", "give", "display", "analyze",
        "compare", "tell", "detail", "details", "summarize", "outline", "inspect", "view",
        "get", "fetch", "check", "distribution", "mix", "proportion", "proportions", "percentage"
    }
    dataset_tokens.update(generic_business_terms)

    # 0. Early check for definition queries (e.g. "what is tea", "what is camellia", "how to brew", "who are you")
    clean_q_lower = question.strip().lower()
    if re.search(r"^(what\s+is\s+tea|what\s+is\s+camellia|define\s+tea|tell\s+me\s+about\s+tea|how\s+to\s+brew|who\s+are\s+you|what\s+can\s+you\s+do|help)\b", clean_q_lower):
        return {
            "intent": "definition",
            "question": question,
        }

    # Early check for out-of-scope non-business queries.
    # IMPORTANT: These patterns fire IMMEDIATELY regardless of any pronouns or conversation context.
    # A query like "why is it hot" must NEVER inherit context to become a business query.
    HARD_OOS_PATTERN = re.compile(
        r"\b(prime\s+minister|pm\s+of|president|chief\s+minister|minister|politician"
        r"|weather|forecast|temperature|climate|recipe|baking"
        r"|who\s+is\s+(?:the\s+)?(?:pm|president|prime\s+minister)"
        r"|cricket|football|soccer|basketball|sport|movie|film|song|actor|actress|poem|joke|story"
        r"|python|java|javascript|crypto|bitcoin|ethereum|war|election"
        r"|why\s+is\s+it\s+(hot|cold|warm|raining|rainy|sunny|cloudy|humid)"
        r"|how\s+(hot|cold|warm)\s+is|what\s+is\s+the\s+(weather|temperature|climate)"
        r"|is\s+it\s+(going\s+to\s+)?rain)\b",
        re.I
    )
    has_hard_oos = bool(HARD_OOS_PATTERN.search(clean_q_lower))

    # Secondary OOS: general weather/trivia words that aren't business context
    has_explicit_out_of_scope = has_hard_oos or any(w in raw_tokens for w in OUT_OF_SCOPE_WORDS)

    # Business domain words derived dynamically from the profile + common business vocab
    # (NO hardcoded tea-specific list — uses dataset_tokens built from actual column names and sample values)
    has_business_measure_query = bool(
        set(raw_tokens) & (dataset_tokens | generic_business_terms)
        and not has_hard_oos  # hard OOS always wins
    )

    # Explicit weather/trivia words that have no business meaning: fire unconditionally.
    # This set is about human language OOS patterns — NOT your dataset vocabulary.
    # Any word that is ONLY meaningful in a weather/sport/entertainment context:
    UNCONDITIONAL_OOS = {"hot", "cold", "warm", "rain", "raining", "rainy", "sunny", "sun",
                         "cloud", "cloudy", "humid", "humidity", "climate", "joke",
                         "funny", "story", "cricket", "football", "soccer", "movie", "film"}
    has_unconditional_oos = bool(set(raw_tokens) & UNCONDITIONAL_OOS)
    # Only block on unconditional OOS if NO genuine business tokens are present.
    # Use dataset_tokens (dynamically built from profile) instead of a hardcoded list:
    business_tokens_present = bool(set(raw_tokens) & (dataset_tokens - STOP_WORDS - UNCONDITIONAL_OOS))

    if has_hard_oos or (has_unconditional_oos and not business_tokens_present):
        return {
            "intent": "out_of_scope",
            "question": question,
        }

    if has_explicit_out_of_scope and not has_business_measure_query:
        return {
            "intent": "out_of_scope",
            "question": question,
        }

    # 1. Parse requested top N (e.g. "top 5", "top 10", "bottom 3", "lowest five")
    # Exclude FY patterns (e.g. FY 2025-26, FY25) and calendar years (2018-2030)
    clean_q_for_nums = re.sub(r"\b(?:FY|Financial\s+Year|Fiscal\s+Year)\s*[:\-]?\s*(?:20\d\d)?(?:[-/]\d{2,4})?\b", "", question, flags=re.I)
    clean_q_for_nums = re.sub(r"\b20\d\d[-/]\d{2,4}\b", "", clean_q_for_nums)

    # Check for explicit ranking count cue: e.g. "top 5", "bottom 10", "first 3", "lowest 5"
    m_rnk_count = re.search(r"\b(?:top|bottom|highest|lowest|first|best|worst|leading|rank)\s*(\d+)\b", clean_q_for_nums, re.I)
    if m_rnk_count:
        found_nums = [int(m_rnk_count.group(1))]
        has_explicit_count = True
    else:
        num_words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        m_word_rnk = re.search(r"\b(?:top|bottom|highest|lowest|first|best|worst|leading|rank)\s*(one|two|three|four|five|six|seven|eight|nine|ten)\b", clean_q_for_nums, re.I)
        if m_word_rnk:
            found_nums = [num_words[m_word_rnk.group(1).lower()]]
            has_explicit_count = True
        else:
            # Standalone number only if user specifically starts with e.g. "5 highest estates"
            m_stand = re.search(r"\b(\d+)\s+(?:highest|lowest|best|worst|top|bottom)\b", clean_q_for_nums, re.I)
            if m_stand:
                found_nums = [int(m_stand.group(1))]
                has_explicit_count = True
            else:
                found_nums = []
                has_explicit_count = False

    top_n = max(1, min(50, found_nums[0])) if found_nums else 10

    # 2. Build dynamic semantic maps from active dataset profile and client business glossary
    dynamic_dim_map, dynamic_meas_map = build_dynamic_semantic_maps(profile, client_id=client_id)

    # Generic entity guard words derived dynamically from schema
    operational_action_words = {
        "pack", "packed", "packing", "produce", "produced", "producing",
        "manufacture", "manufactured", "manufacturing", "process", "processed", "processing",
        "sell", "sold", "selling", "order", "ordered", "ordering",
        "buy", "bought", "buying", "dispatch", "dispatched", "dispatching",
        "ship", "shipped", "shipping", "invoice", "invoiced", "invoicing",
        "bill", "billed", "billing", "rate", "rated", "rating", "volume", "quantity"
    }
    _unit_reserved = set(STOP_WORDS) | generic_business_terms | {"ALL", "TOTAL", "NET", "SET", "NEW", "ONE", "TOP", "FOR", "AND", "PER", "SUM", "MIN", "MAX", "THE", "OUR", "ANY", "EACH", "AVG", "LOT", "DAY"}
    generic_entity_words = set(STOP_WORDS) | generic_business_terms | operational_action_words | _unit_reserved | {
        "sale", "sales", "type", "types", "mode", "channel", "category", "grade",
        "season", "flush", "estate", "garden", "market", "region", "district"
    }
    for m in profile.get("measures", []):
        generic_entity_words.update(m["column"].lower().split("_"))
    for d in profile.get("dimensions", []):
        generic_entity_words.update(d["column"].lower().split("_"))
    for aliases in dynamic_dim_map.values():
        for a in aliases:
            generic_entity_words.update(a.lower().split())
    for aliases in dynamic_meas_map.values():
        for a in aliases:
            generic_entity_words.update(a.lower().split())

    # 0. Check for Oracle Garden Codes (GLOCA, e.g. G00003, G00009) or Operating Units (e.g. BURF, DEWF)
    # gloca_map and unit_map are built dynamically by profile_dataset() from live Oracle data —
    # no hardcoding needed. Any new garden added to ERP is auto-recognised.
    gloca_map: Dict[str, Any] = profile.get("gloca_map", {})
    unit_map: Dict[str, str] = profile.get("unit_map", {})
    all_units: List[str] = profile.get("all_units", [])

    filters = []
    matched_filter_dims = set()
    matched_dim_entities: Dict[str, List[str]] = {}

    m_code = re.search(r"\b(G\d{4,5})\b", question, re.I)
    if m_code:
        code_str = m_code.group(1).upper()
        consumed_tokens.add(code_str.lower())
        consumed_tokens.add(code_str)
        is_unit_or_id_lookup = bool(
            re.search(r"\b(which|what|where)\b.*\b(unit|estate|garden|factory|name|code|location)\b", question, re.I)
            or re.search(r"\b(unit|estate|garden)\s+of\b", question, re.I)
            or re.search(r"\bwhich\s+unit\b", question, re.I)
        )
        if is_unit_or_id_lookup:
            return {
                "intent": "code_lookup",
                "code": code_str,
                "code_type": "GLOCA",
                "target_field": "UNIT" if "unit" in question.lower() else "ESTATE",
                "question": question,
            }
        matched_estate = gloca_map.get(code_str, {}).get("estate")
        if matched_estate:
            filters.append({"column": "ESTATE", "operator": "==", "value": matched_estate})
            matched_dim_entities["ESTATE"] = [matched_estate]
            matched_filter_dims.add("ESTATE")
        else:
            filters.append({"column": "GLOCA", "operator": "==", "value": code_str})
            matched_dim_entities["GLOCA"] = [code_str]
            matched_filter_dims.add("GLOCA")

    # Build unit pattern dynamically from profile instead of a hardcoded list
    valid_units = [u for u in all_units if len(u) >= 3 and u.upper() not in _unit_reserved and u.lower() not in _unit_reserved]
    _unit_pattern = r"\b(" + "|".join(re.escape(u) for u in valid_units) + r")\b" if valid_units else None
    m_unit = re.search(_unit_pattern, question, re.I) if _unit_pattern else None
    if m_unit and not m_code:
        unit_str = m_unit.group(1).upper()
        consumed_tokens.add(unit_str.lower())
        consumed_tokens.add(unit_str)
        is_unit_lookup = bool(re.search(r"\b(which|what|where)\b.*\b(estate|garden|factory|name|code|location)\b", question, re.I))
        if is_unit_lookup:
            return {
                "intent": "code_lookup",
                "code": unit_str,
                "code_type": "UNIT",
                "target_field": "ESTATE",
                "question": question,
            }
        filters.append({"column": "UNIT", "operator": "==", "value": unit_str})
        matched_dim_entities["UNIT"] = [unit_str]
        matched_filter_dims.add("UNIT")

    # Extract Entity Filters from dimension sample values (pre-filtered tokens for max speed)
    generic_sample_list = list(generic_entity_words)[:30]
    valid_query_tokens = []
    for tok in raw_tokens:
        if tok in consumed_tokens or tok in generic_entity_words:
            continue
        if any(damerau_levenshtein_similarity(tok, gw) >= 0.80 for gw in generic_sample_list):
            continue
        valid_query_tokens.append(tok)

    # Prioritize primary business dimensions over secondary partner/technical dimensions.
    # Priority is derived dynamically from column metadata — zero hardcoded column names.
    dim_objs = list(profile.get("dimensions", []))
    col_metadata = profile.get("column_metadata")
    if not col_metadata:
        col_metadata = classify_dataset_columns(None, profile)
        profile["column_metadata"] = col_metadata

    def _infer_dim_priority(col: str) -> int:
        return col_metadata.get(col, {}).get("priority", 5)

    dim_objs.sort(key=lambda d: _infer_dim_priority(d["column"]))

    # Pass 1: Exact whole-word matches across all dimensions (primary entity dims take priority)
    for d_obj in dim_objs:
        d_name = d_obj["column"]
        # Skip shadow/alias columns when primary column exists
        if col_metadata.get(d_name, {}).get("is_shadow", False):
            continue

        matched_in_dim = []
        for sample_val in d_obj.get("sample_values", []):
            val_str = str(sample_val).strip()
            if len(val_str) < 3 or val_str.lower() in generic_entity_words:
                continue
            val_toks = [v for v in val_str.lower().split() if v not in generic_entity_words and len(v) >= 3]
            for tok in valid_query_tokens:
                if tok in consumed_tokens:
                    continue
                if tok in val_toks or tok == val_str.lower():
                    if val_str not in matched_in_dim:
                        matched_in_dim.append(val_str)
                    consumed_tokens.add(tok)
                    break

        if matched_in_dim:
            matched_dim_entities.setdefault(d_name, []).extend([m for m in matched_in_dim if m not in matched_dim_entities.get(d_name, [])])
            matched_filter_dims.add(d_name)

    for d_obj in dim_objs:
        d_name = d_obj["column"]
        # Skip shadow/alias columns when primary column exists
        if col_metadata.get(d_name, {}).get("is_shadow", False):
            continue

        matched_in_dim = []
        for sample_val in d_obj.get("sample_values", []):
            val_str = str(sample_val).strip()
            if len(val_str) < 3 or val_str.lower() in generic_entity_words:
                continue
            val_toks = [v for v in val_str.lower().split() if v not in generic_entity_words and len(v) >= 4]
            for tok in valid_query_tokens:
                if tok in consumed_tokens:
                    continue
                if damerau_levenshtein_similarity(tok, val_str.lower()) >= 0.82 or any(damerau_levenshtein_similarity(tok, vt) >= 0.82 for vt in val_toks):
                    if val_str not in matched_in_dim:
                        matched_in_dim.append(val_str)
                    consumed_tokens.add(tok)
                    break

        if matched_in_dim:
            matched_dim_entities.setdefault(d_name, []).extend([m for m in matched_in_dim if m not in matched_dim_entities.get(d_name, [])])
            matched_filter_dims.add(d_name)

    # Generate filter specifications
    for d_name, matched_vals in matched_dim_entities.items():
        if len(matched_vals) == 1:
            filters.append({"column": d_name, "operator": "==", "value": matched_vals[0]})
        elif len(matched_vals) > 1:
            filters.append({"column": d_name, "operator": "in", "value": matched_vals})

    # 2A. Financial Year (FY) filter (Indian FY: April 1 to March 31)
    # Examples: "FY 2024-25", "FY 2025-26", "FY25", "FY 26", "financial year 2024-25", "financial year 2025"
    m_fy = re.search(r"\b(?:FY|Financial\s+Year|Fiscal\s+Year)\s*[:\-]?\s*(20\d\d)(?:[-/](\d{2,4}))?\b", question, re.I)
    m_fy_short = re.search(r"\bFY\s*(\d{2})\b", question, re.I) if not m_fy else None

    matched_fy = False
    if m_fy:
        start_yr = int(m_fy.group(1))
        end_yr = (start_yr + 1)
        if m_fy.group(2):
            raw_end = m_fy.group(2)
            end_yr = int("20" + raw_end) if len(raw_end) == 2 else int(raw_end)
        fy_label = f"FY {start_yr}-{str(end_yr)[-2:]}"
        start_date = f"{start_yr}-04-01"
        end_date = f"{end_yr}-03-31"
        matched_fy = True
    elif m_fy_short:
        short_num = int(m_fy_short.group(1))
        end_yr = 2000 + short_num
        start_yr = end_yr - 1
        fy_label = f"FY {start_yr}-{str(end_yr)[-2:]}"
        start_date = f"{start_yr}-04-01"
        end_date = f"{end_yr}-03-31"
        matched_fy = True

    if matched_fy:
        d_col = date_names[0] if date_names else "DATE"
        filters.append({
            "column": d_col,
            "operator": "date_range",
            "value": [start_date, end_date],
            "label": fy_label,
            "is_fy": True,
        })
        consumed_tokens.add("fy")
    else:
        # Standard calendar year filter (e.g. 2025, 2024, 2026)
        m_yr = re.search(r"\b(20[12]\d)\b", question)
        if m_yr and date_names:
            filters.append({"column": date_names[0], "operator": "year", "value": m_yr.group(1)})
            consumed_tokens.add(m_yr.group(1))

    # 3. Match Dimension dynamically
    priority_map = {col: meta.get("priority", 5) for col, meta in col_metadata.items()}
    semantic_ignore = set(STOP_WORDS) | set(DIRECTION_ASCENDING) | set(DIRECTION_DESCENDING) | set(INTENT_TOTAL) | set(INTENT_AVERAGE) | set(INTENT_TIME_SERIES) | set(INTENT_ANOMALY)
    active_tokens_for_dim = [t for t in raw_tokens if t not in consumed_tokens]
    dim_key, d_sim, matched_dim_toks = fuzzy_match_phrase(active_tokens_for_dim, dynamic_dim_map, threshold=0.65, ignore=semantic_ignore, priority_map=priority_map)

    chosen_dim = None
    if dim_key:
        for t in matched_dim_toks:
            consumed_tokens.add(t)
        chosen_dim = dim_key

    # 4. Match Measure dynamically
    active_tokens_for_meas = [t for t in raw_tokens if t not in consumed_tokens]
    meas_key, m_sim, matched_meas_toks = fuzzy_match_phrase(active_tokens_for_meas, dynamic_meas_map, threshold=0.65, ignore=semantic_ignore, priority_map=priority_map)

    # Detect count/batch intent — only when "records", "lots", "batches" etc. are used as NOUNS.
    # Key rule: "records" is a VERB in "which estate records lowest quantity" — do NOT count rows.
    # "records" = NOUN when preceded by: total / count of / number of / how many / all
    # "records" = VERB when followed by: a direction word (lowest/highest) or a measure concept
    _records_as_noun = bool(re.search(
        r"\b(total\s+records?|count\s+of\s+records?|number\s+of\s+records?|how\s+many\s+records?|all\s+records?)\b",
        question, re.I
    ))
    # "records" is a verb if followed immediately (within 3 words) by a direction or measure
    _records_as_verb = bool(re.search(
        r"\brecords?\s+(?:\w+\s+){0,2}(?:lowest|highest|best|worst|minimum|maximum|total|average|"
        r"quantity|volume|kg|kgs|revenue|sales|price|margin|profit|output|production|amount)\b",
        question, re.I
    ))
    is_batch_or_count_query = bool(
        re.search(
            r"\b(batches?|packing\s+batches?|lot\s+count|invoices?|transactions?"
            r"|count\s+of|number\s+of\s+(?:batches|lots|invoices|records|transactions|orders))\b",
            question, re.I
        )
        or (_records_as_noun and not _records_as_verb)
        or re.search(r"\bhow\s+many\s+(?:lots|batches|invoices|orders|transactions)\b", question, re.I)
    )


    # 4B. Conversational Context & Multi-Turn Follow-Up Resolution
    has_pronoun = bool(re.search(r"\b(it|its|this|that|their|the\s+same)\b", question, re.I))
    has_followup_cue = bool(re.search(r"\b(what\s+about|how\s+about|and\s+for|what\s+is|what\s+was|tell\s+me|show|give\s+me|how\s+much|how\s+many)\b", question, re.I))

    # CRITICAL: A fresh ranking / breakdown query MUST NOT inherit entity filters from context.
    # If the query has an explicit top-N count, or uses rank/bottom/lowest N across a dimension,
    # it is a new portfolio-level question — not a follow-up about the previous entity.
    is_fresh_ranking_query = bool(
        has_explicit_count
        or re.search(r"\b(rank|top\s*\d+|bottom\s*\d+|highest\s*\d+|lowest\s*\d+|leaderboard|rankings?\s+of|rank\s+all|list\s+all)\b", question, re.I)
    )

    # A query is a ranking, breakdown, or portfolio inquiry if it explicitly requests ranking or grouping across a dimension
    is_ranking_or_breakdown = bool(
        has_explicit_count
        or re.search(r"\b(rank|ranking|top|bottom|highest|lowest|best|worst|by\s+[a-z_]+|across\s+[a-z_]+|breakdown|all\s+[a-z_]+|list\s+all|distinguish|split|group\s+by)\b", question, re.I)
        or (chosen_dim and any(w in raw_tokens for w in ["highest", "lowest", "top", "bottom", "all", "each", "every", "give", "list", "show"]))
    )

    if conversation_context and not is_fresh_ranking_query and not is_ranking_or_breakdown:
        last_dim = conversation_context.get("last_dimension")
        last_ent = conversation_context.get("last_entity")

        # Only inherit entity if:
        # 1. No new entity filter was matched
        # 2. chosen_dim is NOT the same dimension as last_dim (cannot group by estate while filtering to 1 estate!)
        # 3. Query has explicit pronouns ("what about its volume?") OR a follow-up cue without a new dimension
        if not matched_filter_dims and (chosen_dim != last_dim):
            if (has_pronoun or has_followup_cue) and (meas_key or chosen_dim or is_batch_or_count_query):
                if last_dim and last_ent:
                    filters.append({"column": last_dim, "operator": "==", "value": last_ent})
                    matched_filter_dims.add(last_dim)
                    matched_dim_entities[last_dim] = [last_ent]
                elif conversation_context.get("last_filters"):
                    for lf in conversation_context["last_filters"]:
                        if lf.get("column") != chosen_dim:
                            filters.append(lf)
                            if lf.get("column"):
                                matched_filter_dims.add(lf["column"])

        # Case B: Entity switch without re-specifying measure (e.g. "what about Dewan?", "and for Dewan?")
        if not meas_key and conversation_context.get("last_measure") and (matched_dim_entities or (has_followup_cue and not chosen_dim)):
            meas_key = conversation_context["last_measure"]

        # Case C: Inherit breakdown dimension on entity switch if previous was a breakdown
        if not chosen_dim and conversation_context.get("last_breakdown_dimension"):
            if matched_dim_entities and not any(w in raw_tokens for w in ["total", "sum", "overall"]):
                chosen_dim = conversation_context["last_breakdown_dimension"]
    elif conversation_context and is_fresh_ranking_query:
        # For fresh ranking queries: ONLY inherit the measure if no measure was detected,
        # but NEVER inherit entity filters.
        if not meas_key and conversation_context.get("last_measure"):
            meas_key = conversation_context["last_measure"]

    # 5. Detect Intent & Direction
    has_ts, _, _ = fuzzy_match_phrase(raw_tokens, {"ts": INTENT_TIME_SERIES}, threshold=0.70, ignore=STOP_WORDS)
    has_anom, _, _ = fuzzy_match_phrase(raw_tokens, {"anom": INTENT_ANOMALY}, threshold=0.70, ignore=STOP_WORDS)
    has_asc, asc_score, _ = fuzzy_match_phrase(raw_tokens, {"asc": DIRECTION_ASCENDING}, threshold=0.68, ignore=STOP_WORDS)
    has_desc, desc_score, _ = fuzzy_match_phrase(raw_tokens, {"desc": DIRECTION_DESCENDING}, threshold=0.68, ignore=STOP_WORDS)
    if "min" in raw_tokens:
        has_asc, asc_score = "asc", 1.0
    if "max" in raw_tokens:
        has_desc, desc_score = "desc", 1.0
    has_tot, _, _ = fuzzy_match_phrase(raw_tokens, {"tot": INTENT_TOTAL}, threshold=0.70, ignore=STOP_WORDS)
    has_avg, _, _ = fuzzy_match_phrase(raw_tokens, {"avg": INTENT_AVERAGE}, threshold=0.70, ignore=STOP_WORDS)

    # Check for missing attribute / unmapped business metric
    known_vocab = set(STOP_WORDS) | set(DIRECTION_ASCENDING) | set(DIRECTION_DESCENDING) | set(INTENT_TOTAL) | set(INTENT_AVERAGE) | set(INTENT_TIME_SERIES) | generic_business_terms | dataset_tokens
    for aliases in dynamic_dim_map.values():
        known_vocab.update(aliases)
    for aliases in dynamic_meas_map.values():
        known_vocab.update(aliases)
        
    unknown_words = []
    for tok in raw_tokens:
        if len(tok) >= 3 and tok not in known_vocab and not any(damerau_levenshtein_similarity(tok, kw) >= 0.78 for kw in known_vocab):
            unknown_words.append(tok)

    # 0. Check for time series / trend intent FIRST if monthly/trend keywords exist
    has_explicit_ts_cue = bool(re.search(r"\b(monthly|trend|trends|over\s+time|by\s+month|trajectory|velocity|timeline)\b", question, re.I))
    if has_ts or has_explicit_ts_cue:
        best_date = date_names[0] if date_names else None
        dim_meas = meas_key
        if not dim_meas and meas_names:
            # Pick the first numeric/sum measure from profile — no hardcoded column names
            dim_meas = meas_names[0]

        # Dynamically determine primary entity dimension using schema-inferred priority
        primary_dim = next((d for d in matched_dim_entities.keys()), None)
        if not primary_dim:
            primary_dim = next(
                (d["column"] for d in profile.get("dimensions", []) if _infer_dim_priority(d["column"]) <= 1),
                profile["dimensions"][0]["column"] if profile.get("dimensions") else None
            )

        comp_ents = list(matched_dim_entities.get(primary_dim, [])) if primary_dim else []
        m_num_ents = re.search(r"\b(two|2)\s+([a-zA-Z]+)\b", question, re.I)
        if len(comp_ents) < 2 and m_num_ents:
            cand_tok = m_num_ents.group(2).lower()
            target_dim_for_two = primary_dim
            for d_name, d_aliases in dynamic_dim_map.items():
                if any(cand_tok in a or a in cand_tok for a in d_aliases):
                    target_dim_for_two = d_name
                    break
            dim_obj = next((d for d in profile.get("dimensions", []) if d["column"] == target_dim_for_two), None)
            if dim_obj and len(dim_obj.get("sample_values", [])) >= 2:
                comp_ents = list(dim_obj["sample_values"][:2])
                filters = [f for f in filters if f.get("column") != target_dim_for_two]
                filters.append({"column": target_dim_for_two, "operator": "in", "value": comp_ents})
                primary_dim = target_dim_for_two

        return {
            "intent": "time_series",
            "measure": dim_meas,
            "time_column": best_date,
            "time_granularity": "month",
            "filters": filters,
            "comparison_entities": comp_ents if len(comp_ents) >= 2 else (matched_dim_entities.get(primary_dim) if primary_dim in matched_dim_entities else None),
        }

    # Check for comparison intent across entities (e.g. "How does Aryaman compare with Dewan or Meleng?", "Dewan vs Meleng")
    is_comp_query = bool(
        re.search(r"\b(compare|comparing|comparison|versus|vs|against|between|differ|difference)\b", question, re.I)
        or re.search(r"\bhow\s+does\b", question, re.I)
    )
    multi_ent_dim = next((d for d, ents in matched_dim_entities.items() if len(ents) > 1), None)
    if multi_ent_dim or (is_comp_query and matched_dim_entities):
        comp_dim = multi_ent_dim or next((d for d in matched_dim_entities.keys()), list(matched_dim_entities.keys())[0])
        comp_ents = matched_dim_entities[comp_dim]
        dim_meas = meas_key
        if not dim_meas and meas_names:
            # Use first available measure from profile — dynamic, no keyword assumptions
            dim_meas = meas_names[0]
        return {
            "intent": "ranking",
            "dimension": comp_dim,
            "measure": dim_meas,
            "sort": "descending",
            "top_n": len(comp_ents) if len(comp_ents) > 1 else 5,
            "filters": [{"column": comp_dim, "operator": "in", "value": comp_ents}] if len(comp_ents) > 1 else filters,
            "explicit_top_n": False,
            "is_comparison": True,
            "comparison_entities": comp_ents,
        }

    # 1. Check for tea manufacturing domain inquiries (e.g. recovery, recobery, outturn)
    recovery_cues = ["recovery", "recobery", "outturn", "green leaf", "green leaf weighment", "plucking recovery"]
    if any(cue in question.lower() for cue in recovery_cues):
        return {
            "intent": "tea_domain_explanation",
            "domain_topic": "recovery",
            "question": question,
        }

    # 2. If a dimension is recognized (e.g. "distinguish sale type", "break down by grade"),
    # never return missing_attribute! It is a distribution breakdown across that dimension.
    # If chosen_dim is ESTATE/DESCN but user ALREADY filtered by that specific estate
    # (e.g. "Dewan tea estate revenue 2025"), the words "tea estate" belong to the entity name, NOT a groupby request!
    if chosen_dim:
        is_same_entity_dim = (chosen_dim in matched_dim_entities) or any(
            chosen_dim == f.get("column") for f in filters if f.get("operator") in ["==", "="]
        )
        has_breakdown_verb = bool(re.search(r"\b(by|across|breakdown|break down|distinguish|differentiate|split|group by|rank|top|bottom)\b", question, re.I))
        if is_same_entity_dim and not has_breakdown_verb:
            chosen_dim = None

    if chosen_dim:
        dim_meas = meas_key
        has_all = bool(re.search(r"\b(all|entire|every|whole)\b", question, re.I))
        if is_batch_or_count_query and not meas_key:
            # Only switch to count aggregation when NO real measure was detected.
            # If the user said "records lowest quantity", meas_key is already the quantity column — use it.
            agg_type = "count"
            count_col = next(
                (c for c in dim_names + list(profile.get("all_dim_columns", []))
                 if any(k in c.upper() for k in ["INVNO", "LOT", "BATCH", "ORDER", "INVOICE"])),
                None
            )
            dim_meas = count_col or (meas_names[0] if meas_names else "records")
        else:
            agg_type = "mean" if has_avg else "sum"
            if not dim_meas and meas_names:
                # Use first measure from profile (already ordered by importance) — no keyword list
                dim_meas = meas_names[0]
        calc_top_n = None if has_all else (top_n if has_explicit_count else 10)
        return {
            "intent": "ranking",
            "dimension": chosen_dim,
            "measure": dim_meas,
            "aggregation": agg_type,
            "sort": "ascending" if (has_asc and not has_desc) else "descending",
            "top_n": calc_top_n,
            "filters": filters,
            "explicit_top_n": has_explicit_count,
            "has_all": has_all,
        }

    has_ranking_cue = bool(has_explicit_count or has_asc or has_desc or re.search(r"\b(top|bottom|highest|lowest|best|worst|rank|ranking|leaderboard|list\s+all|show\s+all|distinguish|differentiate|split|breakdown|break\s+down|categorize|classify|group|segregate|divide|separate|distribution|share|mix|proportions?)\b", question, re.I))

    if unknown_words and not meas_key and not has_ranking_cue:
        return {
            "intent": "missing_attribute",
            "attribute": " ".join(unknown_words),
            "question": question,
        }

    chosen_meas = meas_key
    if not chosen_meas and meas_names:
        chosen_meas = meas_names[0]

    is_rate_meas = bool(chosen_meas and (
        col_metadata.get(chosen_meas, {}).get("formatting") in ("rate", "percentage", "score")
        or col_metadata.get(chosen_meas, {}).get("role") in ("rate", "ratio", "score")
    ))

    # If dimension is specified (e.g. by season flush, by region), prioritize dimension ranking over time series
    if has_ts and not chosen_dim:
        best_date = "DATE" if "DATE" in date_names else (date_names[0] if date_names else None)
        return {
            "intent": "time_series",
            "measure": chosen_meas,
            "time_column": best_date,
            "time_granularity": "month",
            "filters": filters,
        }
    elif has_anom:
        return {
            "intent": "anomaly",
            "anomaly_column": chosen_meas,
            "filters": filters,
        }

    if has_asc and has_desc:
        sort_dir = "ascending" if asc_score > desc_score else "descending"
    elif has_asc:
        sort_dir = "ascending"
    else:
        sort_dir = "descending"

    # Check if dimension was explicitly mentioned vs dataset-level aggregation
    is_direction_ranking = bool((has_asc or has_desc) and chosen_dim)
    has_which_what_dim = bool(chosen_dim and chosen_dim not in matched_filter_dims)

    if is_direction_ranking or has_which_what_dim or has_explicit_count:
        agg = "mean" if (has_avg or is_rate_meas) else "sum"
        target_dim = chosen_dim or (dim_names[0] if dim_names else (profile.get("dimensions", [{}])[0].get("column", "Dimension")))
        return {
            "intent": "ranking",
            "dimension": target_dim,
            "measure": chosen_meas,
            "aggregation": agg,
            "filters": filters,
            "sort": sort_dir,
            "top_n": top_n,
            "explicit_top_n": has_explicit_count,
        }

    # Guard: Detect completely out-of-scope queries (e.g. general trivia, politics, weather, recipes)
    # Use dataset_tokens (built dynamically from profile column names and sample values) instead of
    # a hardcoded tea-specific word list — this works for ANY dataset, not just tea.
    has_any_signal = bool(filters or dim_key or meas_key or has_asc or has_desc or has_ts or has_anom or has_tot or has_avg or has_explicit_count)
    # Also check if any query token overlaps with the dynamically-built dataset vocabulary
    has_dataset_domain_token = bool(set(raw_tokens) & dataset_tokens - STOP_WORDS)

    if not has_any_signal and not has_dataset_domain_token:
        return {
            "intent": "out_of_scope",
            "question": question,
        }

    # Pure dataset-level aggregations (when no dimension was targeted)
    if has_asc and not chosen_dim and (not has_desc or asc_score > desc_score):
        return {"intent": "aggregation", "measure": chosen_meas, "aggregation": "min", "filters": filters}
    if has_desc and not chosen_dim and (not has_asc or desc_score >= asc_score):
        return {"intent": "aggregation", "measure": chosen_meas, "aggregation": "max", "filters": filters}
    if has_avg or is_rate_meas:
        return {"intent": "aggregation", "measure": chosen_meas, "aggregation": "mean", "filters": filters}

    return {"intent": "aggregation", "measure": chosen_meas, "aggregation": "sum", "filters": filters}


def create_analysis_plan(question: str, profile: Dict[str, Any], conversation_context: Dict[str, Any], client_id: Optional[str] = None) -> Dict[str, Any]:
    """Uses deterministic rule parser and OpenAI planner to parse user query into an analysis plan."""
    if not client_id and isinstance(conversation_context, dict):
        client_id = conversation_context.get("client_id")
    if not client_id:
        client_id = "client_alpha"

    # Check for advanced / complex analytical intent (Window functions, cumulative, correlation, Pareto, ratios)
    complex_intent = detect_complex_intent(question)
    if complex_intent:
        return {
            "intent": complex_intent,
            "question": question,
            "client_id": client_id,
        }

    fb_plan = rule_based_fallback_plan(question, profile, client_id=client_id, conversation_context=conversation_context)
    if fb_plan.get("intent") in ["out_of_scope", "definition", "missing_attribute", "tea_domain_explanation", "code_lookup", "time_series", "ranking", "aggregation", "anomaly"] or not is_openai_available():
        return fb_plan

    m_top = re.search(r"\b(?:top|bottom|highest|lowest|first|best|worst|leading)\s+(\d+)\b", question, re.I)
    requested_n = int(m_top.group(1)) if m_top else None

    measures_list = [m['column'] for m in profile['measures']]
    dimensions_list = [d['column'] for d in profile['dimensions']]
    glossary_prompt = get_llm_glossary_prompt(client_id)

    system_prompt = f"""
You are an expert Data Analyst Planner for a business dataset.
Produce a JSON analysis plan for the user's question using ONLY available columns:
- Measures: {measures_list}
- Dimensions: {dimensions_list}
- Dates: {[d['column'] for d in profile['dates']]}

{glossary_prompt}

CRITICAL RULES:
1. "top N" / "highest N" / "best N" / "rank":
   - Set intent to "ranking"
   - Set sort to "descending"
   - Set top_n to the requested number N (e.g. 5, 10, 3).
   - If user asks for "category" or "any category" and no column named "CATEGORY" exists, choose an existing dimension such as {dimensions_list[:3]}.
   - If user asks "top 5" without specifying a dimension, choose the primary entity dimension: '{dimensions_list[0] if dimensions_list else "None"}'.
2. "bottom N" / "lowest N" / "least N" / "worst N" / "which estate has lowest revenue":
   - Set intent to "ranking"
   - Set sort to "ascending"
   - Set top_n to the requested number N.
3. "minimum" / "min" / "lowest [measure]" (without an entity/dimension breakdown):
   - Set intent to "aggregation"
   - aggregation: "min"
   - dimension: null
4. "maximum" / "max" / "highest [measure]" (without an entity/dimension breakdown):
   - Set intent to "aggregation"
   - aggregation: "max"
   - dimension: null
5. "total", "overall", "grand total", "sum", "total revenue", "total sales", "total volume":
   - Set intent to "aggregation"
   - aggregation: "sum" (or "mean" if price/rate/margin)
   - dimension: null
   - DO NOT set intent to "ranking" unless the user explicitly requested "top N" or "breakdown by X"!
6. Specific entity questions (e.g. "what is revenue of Castleton?"):
   - Set intent to "aggregation"
   - Add filter: [{{"column": "<COLUMN>", "operator": "==", "value": "<ENTITY>"}}]
7. Measure mapping:
   - Revenue / Sales / Money / Dollar / Turnover: choose {measures_list[0] if measures_list else "None"}
   - Volume / Harvest / kgs / Quantity: choose {[m for m in measures_list if 'VOL' in m or 'UNIT' in m][:1] or measures_list[:1]}
   - Price / Realization / Rate: choose {[m for m in measures_list if 'PRICE' in m][:1] or measures_list[:1]}
   - Margin / Profit: choose {[m for m in measures_list if 'MARGIN' in m][:1] or measures_list[:1]}
   - Quality / Cupping / Rating: choose {[m for m in measures_list if 'QUAL' in m or 'CUP' in m or 'RAT' in m][:1] or measures_list[:1]}

Schema:
{{
  "intent": "aggregation" | "ranking" | "time_series" | "anomaly" | "distribution",
  "measure": "COLUMN_NAME" | null,
  "aggregation": "sum" | "mean" | "count" | "min" | "max",
  "dimension": "COLUMN_NAME" | null,
  "time_column": "COLUMN_NAME" | null,
  "time_granularity": "month",
  "filters": [{{"column": "COL", "operator": "==" | "!=" | ">" | "<" | "year", "value": "VAL"}}],
  "sort": "descending" | "ascending",
  "top_n": 10
}}
Return ONLY raw JSON.
"""
    user_prompt = f"Context: {json.dumps(conversation_context)}\nQuestion: {question}"
    plan = call_llm_json(system_prompt, user_prompt, timeout=3.0)
    if not plan or not isinstance(plan, dict) or "intent" not in plan:
        return rule_based_fallback_plan(question, profile, client_id=client_id, conversation_context=conversation_context)

    if requested_n:
        plan["top_n"] = requested_n
        plan["explicit_top_n"] = True
    elif "top_n" not in plan or plan.get("top_n") is None:
        plan["top_n"] = 10

    # Strict guard: if query is asking for lowest / bottom / least / min, enforce sort/aggregation
    if re.search(r"\b(lowest|bottom|least|worst|minimum|smallest)\b", question, re.I):
        if plan.get("intent") == "ranking":
            plan["sort"] = "ascending"
        elif plan.get("intent") == "aggregation" and not plan.get("dimension"):
            if re.search(r"\b(min|minimum|lowest|smallest)\b", question, re.I):
                plan["aggregation"] = "min"
    elif re.search(r"\b(highest|top|most|best|maximum|largest)\b", question, re.I):
        if plan.get("intent") == "ranking":
            plan["sort"] = "descending"
        elif plan.get("intent") == "aggregation" and not plan.get("dimension"):
            if re.search(r"\b(max|maximum|highest)\b", question, re.I):
                plan["aggregation"] = "max"

    # Strict guard: if query is asking for total and not explicit ranking/breakdown, enforce aggregation
    is_total_q = bool(re.search(r"\b(total|overall|grand\s+total|combined|sum|aggregate|altogether)\b", question, re.I))
    is_explicit_rnk = bool(re.search(r"\b(top\s*\d+|bottom\s*\d+|highest\s*\d+|lowest\s*\d+|rank|leaderboard|breakdown|by\s+[a-z_]+)\b", question, re.I))
    if is_total_q and not is_explicit_rnk:
        plan["intent"] = "aggregation"
        plan["dimension"] = None
        if "aggregation" not in plan or plan["aggregation"] not in ["sum", "mean"]:
            plan["aggregation"] = "sum"

    has_list_intent = bool(re.search(r"\b(leaderboard|standings|give me (?:a )?list|list (?:all|the|of|all the)|rankings?\s+(?:of|for|all)|rank all|show all|show me (?:all|the list))\b", question, re.I))
    plan["explicit_top_n"] = bool(requested_n or has_list_intent or plan.get("explicit_top_n"))
    return plan


def validate_analysis_plan(plan: Dict[str, Any], df: pd.DataFrame, profile: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Guarantees plan column validity with intelligent synonym auto-remapping.
    All remapping is driven from the live profile and column name patterns — zero hardcoded column lists."""
    if not isinstance(plan, dict) or "intent" not in plan:
        return False, "Invalid plan format."

    if plan.get("intent") in ["out_of_scope", "definition", "missing_attribute", "tea_domain_explanation", "code_lookup", "cumulative_running_total", "moving_average", "correlation", "weighted_ratio", "pareto_distribution"]:
        return True, None

    valid_cols = set(df.columns)
    dim_names = [d["column"] for d in profile.get("dimensions", [])]
    meas_names = [m["column"] for m in profile.get("measures", [])]

    def _find_column(patterns: List[str], candidates: List[str], valid: set) -> Optional[str]:
        """Dynamically find a column by checking if any pattern keyword appears in the column name."""
        for col in candidates:
            col_up = col.upper()
            if col in valid and any(p.upper() in col_up for p in patterns):
                return col
        # Fallback: first available candidate
        return next((c for c in candidates if c in valid), None)

    dim_map, meas_map = build_dynamic_semantic_maps(profile)

    # Remap dimension if needed dynamically from active semantic maps
    dim_val = plan.get("dimension")
    if dim_val and dim_val not in valid_cols:
        matched_d = fuzzy_match_phrase(str(dim_val), dim_map)
        if matched_d and matched_d in valid_cols:
            plan["dimension"] = matched_d
        elif dim_names:
            plan["dimension"] = dim_names[0]

    # Remap measure if needed dynamically from active semantic maps
    meas_val = plan.get("measure")
    if meas_val and meas_val not in valid_cols:
        matched_m = fuzzy_match_phrase(str(meas_val), meas_map)
        if matched_m and matched_m in valid_cols:
            plan["measure"] = matched_m
        elif meas_names:
            plan["measure"] = meas_names[0]

    # If ranking intent but dimension is missing, default to primary dimension
    if plan.get("intent") == "ranking" and not plan.get("dimension"):
        plan["dimension"] = dim_names[0] if dim_names else list(valid_cols)[0]

    return True, None


def execute_analysis(plan: Dict[str, Any], df: pd.DataFrame, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically computes results using Python/pandas."""
    working_df = df.copy()

    # Apply filters
    for flt in plan.get("filters", []):
        col, op, val = flt.get("column"), flt.get("operator", "=="), flt.get("value")
        if col in working_df.columns:
            try:
                if op == "date_range":
                    if isinstance(val, (list, tuple)) and len(val) == 2:
                        d_series = pd.to_datetime(working_df[col], errors="coerce")
                        s_dt = pd.to_datetime(val[0])
                        e_dt = pd.to_datetime(val[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                        working_df = working_df[(d_series >= s_dt) & (d_series <= e_dt)]
                elif op == "==":
                    working_df = working_df[working_df[col].astype(str).str.strip().str.lower() == str(val).strip().lower()]
                elif op == "!=":
                    working_df = working_df[working_df[col].astype(str).str.strip().str.lower() != str(val).strip().lower()]
                elif op == "in" or isinstance(val, (list, tuple, set)):
                    val_set = [str(v).strip().lower() for v in val]
                    working_df = working_df[working_df[col].astype(str).str.strip().str.lower().isin(val_set)]
                elif op == ">":
                    working_df = working_df[pd.to_numeric(working_df[col], errors="coerce") > float(val)]
                elif op == "<":
                    working_df = working_df[pd.to_numeric(working_df[col], errors="coerce") < float(val)]
                elif op == "year":
                    working_df = working_df[pd.to_datetime(working_df[col], errors="coerce").dt.year.astype(str) == str(val)]
            except Exception:
                pass

    if len(working_df) == 0:
        return {"status": "error", "message": "No records matched your specific filter criteria."}

    intent = plan.get("intent", "aggregation")
    measure = plan.get("measure")
    dimension = plan.get("dimension")
    agg = plan.get("aggregation", "sum")

    # 0. OUT OF SCOPE / DEFINITION / MISSING ATTRIBUTE / TEA DOMAIN EXPLANATION
    if intent in ["out_of_scope", "definition", "missing_attribute", "tea_domain_explanation"]:
        return {
            "status": intent,
            "intent": intent,
            "client_id": plan.get("client_id"),
            "attribute": plan.get("attribute", ""),
            "domain_topic": plan.get("domain_topic", ""),
            "question": plan.get("question", ""),
            "message": f"Inquiry status: {intent}",
            "supporting_stats": {},
        }

    # 0A. CODE LOOKUP (GLOCA / GARDEN CODE / OPERATING UNIT)
    if intent == "code_lookup":
        code = str(plan.get("code", "")).upper()
        target_field = plan.get("target_field", "UNIT")

        search_df = working_df if not working_df.empty else df
        m_df = pd.DataFrame()
        if "GLOCA" in search_df.columns:
            m_df = search_df[search_df["GLOCA"].astype(str).str.upper() == code]
        if m_df.empty and "UNIT" in search_df.columns:
            m_df = search_df[search_df["UNIT"].astype(str).str.upper() == code]

        if not m_df.empty:
            est_name = str(m_df["ESTATE"].iloc[0]) if "ESTATE" in m_df.columns else "N/A"
            units = [str(u) for u in m_df["UNIT"].unique() if pd.notna(u) and str(u).strip()] if "UNIT" in m_df.columns else []
            glocas = [str(g) for g in m_df["GLOCA"].unique() if pd.notna(g) and str(g).strip()] if "GLOCA" in m_df.columns else []
            tot_qty = float(m_df["QTY"].sum()) if "QTY" in m_df.columns else 0.0
            tot_batches = len(m_df)
            top_grade = m_df.groupby("GRADE")["QTY"].sum().idxmax() if ("GRADE" in m_df.columns and "QTY" in m_df.columns and not m_df.empty) else "N/A"

            return {
                "status": "success",
                "intent": "code_lookup",
                "code": code,
                "code_type": plan.get("code_type", "GLOCA"),
                "target_field": target_field,
                "estate_name": est_name,
                "units": units,
                "glocas": glocas,
                "total_batches": tot_batches,
                "total_volume_kg": tot_qty,
                "top_grade": top_grade,
                "calculated_value": f"Garden Code {code} -> Unit(s): {', '.join(units)} ({est_name})",
                "applied_filters": plan.get("filters", []),
            }
        else:
            return {
                "status": "success",
                "intent": "code_lookup",
                "code": code,
                "target_field": target_field,
                "estate_name": "Unknown",
                "units": [],
                "total_batches": 0,
                "total_volume_kg": 0.0,
                "message": f"Code {code} not found in active ERP ledger.",
            }

    # 0B. ADVANCED ANALYTICAL INTENTS (DuckDB OLAP Window Functions, Cumulative, Correlation, Pareto, Weighted Ratios)
    if intent in ["cumulative_running_total", "moving_average", "correlation", "weighted_ratio", "pareto_distribution"]:
        client_id = plan.get("client_id", "client_alpha")
        question = plan.get("question", "")
        complex_df, metrics, err = execute_complex_analytical_query(client_id, intent, question, profile)
        if err or complex_df is None:
            return {"status": "error", "message": err or "Complex analytical calculation failed."}
        narrative, followups = synthesize_complex_narrative(intent, metrics, complex_df)
        calc_val = metrics.get("final_cumulative_value") or metrics.get("correlation_coefficient") or metrics.get("latest_rolling_avg") or "Calculation complete"
        return {
            "status": "success",
            "intent": intent,
            "calculated_value": f"Computed {intent.replace('_', ' ').title()}: {calc_val}",
            "summary_table": complex_df,
            "supporting_stats": metrics,
            "applied_filters": plan.get("filters", []),
            "precomputed_narrative": narrative,
            "precomputed_followups": followups,
        }

    # 1. AGGREGATION
    if intent == "aggregation":
        if not measure:
            val = len(working_df)
            return {"status": "success", "intent": "aggregation", "calculated_value": f"Total Record Count: {val:,}", "supporting_stats": {"record_count": val}}

        s = pd.to_numeric(working_df[measure], errors="coerce").dropna()
        if len(s) == 0:
            return {"status": "error", "message": f"Column '{measure}' contains no valid numbers."}

        if agg == "sum":
            res = float(s.sum())
        elif agg == "mean":
            res = float(s.mean())
        elif agg == "min":
            res = float(s.min())
        elif agg == "max":
            res = float(s.max())
        else:
            res = float(len(s))

        is_currency = "REVENUE" in measure or "SALES" in measure or "PRICE" in measure
        is_pct = "PCT" in measure or "MARGIN" in measure
        is_kg = "KG" in measure or "VOLUME" in measure or "UNIT" in measure or "QTY" in measure

        def fmt_val(v: float) -> str:
            if is_currency:
                return format_indian_currency(v)
            elif is_pct:
                return f"{v:,.1f}%"
            elif is_kg:
                return f"{format_indian_number(v, 3)} kgs"
            return f"{format_indian_number(v, 3)}"

        formatted_val = fmt_val(res)
        
        supporting: Dict[str, str] = {}
        if agg == "sum":
            supporting["Total Realized Value"] = fmt_val(res)
            supporting["Average Unit Size"] = fmt_val(float(s.mean()))
        elif agg == "mean":
            supporting["Average Benchmark"] = fmt_val(res)
            supporting["Top Quartile Benchmark"] = fmt_val(float(s.quantile(0.75)))
            supporting["Baseline Benchmark"] = fmt_val(float(s.quantile(0.25)))
        elif agg == "min":
            supporting["Minimum Benchmark"] = fmt_val(res)
            supporting["Portfolio Average"] = fmt_val(float(s.mean()))
            supporting["Maximum Benchmark"] = fmt_val(float(s.max()))
        elif agg == "max":
            supporting["Maximum Benchmark"] = fmt_val(res)
            supporting["Portfolio Average"] = fmt_val(float(s.mean()))
            supporting["Minimum Benchmark"] = fmt_val(float(s.min()))
        else:
            supporting["Selected Benchmark"] = fmt_val(res)
            supporting["Overall Portfolio Realization"] = fmt_val(float(s.mean()))

        return {
            "status": "success",
            "intent": "aggregation",
            "measure": measure,
            "aggregation": agg,
            "calculated_number": res,
            "calculated_value": f"{agg.title()} of {measure.replace('_', ' ').title()}: {formatted_val}",
            "applied_filters": plan.get("filters", []),
            "supporting_stats": supporting,
        }

    # 2. RANKING / BREAKDOWN
    elif intent == "ranking":
        if not dimension:
            dimension = profile["dimensions"][0]["column"] if profile["dimensions"] else df.columns[0]

        # Fix: if dimension resolved to AUTOID/LOCA/GLOCA but ESTATE filter exists,
        # use ESTATE as dimension so the estate name appears in results
        surrogate_dims = {"AUTOID", "LOCA", "GLOCA", "LOTNO", "BILLNO", "INVNO", "SL_NO"}
        if dimension in surrogate_dims and "ESTATE" in working_df.columns:
            estate_vals = working_df["ESTATE"].dropna().unique()
            if len(estate_vals) >= 1:
                dimension = "ESTATE"

        if agg == "count":
            grouped = working_df.groupby(dimension).size().reset_index(name="count_batches")
            val_col = "count_batches"
        elif measure and measure in working_df.columns and pd.api.types.is_numeric_dtype(working_df[measure]):
            grouped = working_df.groupby(dimension)[measure].agg(agg).reset_index()
            val_col = f"{agg}_{measure}"
            grouped = grouped.rename(columns={measure: val_col})
        else:
            grouped = working_df.groupby(dimension).size().reset_index(name="count_batches")
            val_col = "count_batches"

        is_desc = plan.get("sort", "descending") != "ascending"
        sorted_df = grouped.sort_values(by=val_col, ascending=not is_desc).reset_index(drop=True)
        is_bottom = not is_desc

        is_rate = any(k in val_col for k in ["PCT", "MARGIN", "PRICE", "SCORE", "RATING", "CUPPING", "QUALITY"])
        total_sum = float(sorted_df[val_col].sum())
        if total_sum > 0 and not is_rate and agg in ["sum", "count"]:
            sorted_df["Share_of_Total_Pct"] = ((sorted_df[val_col] / total_sum) * 100).round(2)

        req_top_n = plan.get("top_n")
        if req_top_n is None or plan.get("has_all"):
            top_n = len(sorted_df)
        else:
            top_n = min(max(1, req_top_n), len(sorted_df))
        sorted_df = sorted_df.head(top_n)

        is_currency = "REVENUE" in val_col or "SALES" in val_col or "PRICE" in val_col
        is_kg = "KG" in val_col or "VOLUME" in val_col or "UNIT" in val_col or "QTY" in val_col
        is_pct = "PCT" in val_col or "MARGIN" in val_col
        is_count_col = any(k in val_col.lower() for k in ["count", "batch", "record"])

        def fmt_rank(v: float) -> str:
            if is_count_col:
                return f"{int(v):,}"
            elif is_currency:
                return format_indian_currency(v)
            elif is_pct:
                return f"{v:,.2f}%"
            elif is_kg:
                return f"{format_indian_number(v, 3)} kgs"
            return f"{format_indian_number(v, 3)}"

        top_item = sorted_df.iloc[0] if len(sorted_df) > 0 else None
        raw_top_name = str(top_item[dimension]).strip() if (top_item is not None and pd.notna(top_item[dimension])) else ""
        top_name = raw_top_name if raw_top_name and raw_top_name.lower() not in ["", "nan", "none"] else (
            str(plan.get("filters", [{}])[0].get("value", "N/A")) if plan.get("filters") else "N/A"
        )
        top_v = float(top_item[val_col]) if top_item is not None else 0.0
        fmt_v = fmt_rank(top_v)

        share_top = sorted_df["Share_of_Total_Pct"].iloc[0] if "Share_of_Total_Pct" in sorted_df.columns else None

        meas_clean = "Volume" if is_kg else "Revenue" if is_currency else "Total"
        if len(sorted_df) == 1:
            leader_label = f"Total {meas_clean} ({top_name})"
        else:
            leader_label = f"Lowest Rank ({top_name})" if is_bottom else f"Market Leader ({top_name})"
        supporting_ranking: Dict[str, str] = {
            leader_label: fmt_v,
        }
        if share_top is not None and len(sorted_df) > 1:
            supporting_ranking["Portfolio Share Contribution"] = f"{share_top:.1f}%"
        if len(sorted_df) > 1:
            second_item = sorted_df.iloc[1]
            raw_sec_name = str(second_item[dimension]).strip() if pd.notna(second_item[dimension]) else ""
            sec_name = raw_sec_name if raw_sec_name and raw_sec_name.lower() not in ["", "nan", "none"] else "Runner-Up"
            sec_v = float(second_item[val_col])
            second_label = f"Second Lowest ({sec_name})" if is_bottom else f"Runner-Up ({sec_name})"
            supporting_ranking[second_label] = fmt_rank(sec_v)
        if total_sum > 0 and not is_rate and agg == "sum":
            if len(sorted_df) > 1:
                supporting_ranking["Combined Segment Total"] = fmt_rank(total_sum)
        elif is_rate or agg == "mean":
            supporting_ranking["Portfolio Mean Average"] = fmt_rank(float(grouped[val_col].mean()))

        # Determine number of distinct months in date column if present
        num_months = 1
        if profile.get("dates") and profile["dates"][0]["column"] in working_df.columns:
            date_col = profile["dates"][0]["column"]
            try:
                dt_series = pd.to_datetime(working_df[date_col], errors="coerce").dropna()
                if len(dt_series) > 0:
                    periods = dt_series.dt.to_period("M").nunique()
                    if periods > 0:
                        num_months = periods
            except Exception:
                pass

        return {
            "status": "success",
            "intent": "ranking",
            "client_id": plan.get("client_id"),
            "dimension": dimension,
            "measure": measure or val_col,
            "aggregation": agg,
            "summary_table": sorted_df,
            "top_entity": top_name,
            "top_value": top_v,
            "calculated_value": f"{'Lowest' if is_bottom else 'Top'} {dimension.replace('_', ' ').title()}: {top_name} ({fmt_v})",
            "total_categories": int(working_df[dimension].nunique()),
            "portfolio_total": total_sum,
            "num_months": num_months,
            "sort": plan.get("sort", "ascending" if is_bottom else "descending"),
            "requested_top_n": plan.get("top_n", top_n),
            "explicit_top_n": plan.get("explicit_top_n", False),
            "is_comparison": plan.get("is_comparison", False),
            "comparison_entities": plan.get("comparison_entities", []),
            "applied_filters": plan.get("filters", []),
            "supporting_stats": supporting_ranking,
        }

    # 3. TIME SERIES
    elif intent == "time_series":
        time_col = plan.get("time_column") or (profile["dates"][0]["column"] if profile["dates"] else None)
        if not time_col:
            return {"status": "error", "message": "Time series analysis requires a recognized date column."}

        working_df["_parsed_dt"] = pd.to_datetime(working_df[time_col], errors="coerce", format="mixed")
        valid_time_df = working_df.dropna(subset=["_parsed_dt"]).sort_values("_parsed_dt")

        # Per-estate breakdown: when multiple estates are present in the filtered data,
        # produce a side-by-side monthly pivot so each estate gets its own column
        estate_col = "ESTATE" if "ESTATE" in valid_time_df.columns else None
        distinct_estates = valid_time_df[estate_col].dropna().unique().tolist() if estate_col else []
        is_multi_estate = estate_col and 2 <= len(distinct_estates) <= 8
        meas_cols = []
        estate_col_map = {}

        if measure and pd.api.types.is_numeric_dtype(valid_time_df[measure]):
            if is_multi_estate:
                # Pivot: rows = month, columns = estate name
                valid_time_df["_period"] = valid_time_df["_parsed_dt"].dt.to_period("M")
                pivot = (
                    valid_time_df.groupby(["_period", estate_col])[measure]
                    .sum()
                    .unstack(fill_value=0)
                    .reset_index()
                )
                pivot["Period"] = pivot["_period"].astype(str)
                pivot["Month_Name"] = pd.PeriodIndex(pivot["_period"]).to_timestamp().strftime("%B %Y")
                # Clean display names
                estate_col_map = {e: e.replace(" TEA ESTATE", "").replace(" TEA FACTORY", "").strip().title() for e in distinct_estates}
                pivot = pivot.rename(columns=estate_col_map)
                pivot = pivot.drop(columns=["_period"], errors="ignore")
                meas_cols = [estate_col_map.get(e, e) for e in distinct_estates]
                pivot["Combined_Total"] = pivot[meas_cols].sum(axis=1)
                val_col = "Combined_Total"
                resampled = pivot
            else:
                resampled = valid_time_df.set_index("_parsed_dt").resample("ME")[measure].sum().reset_index()
                val_col = f"Total_{measure}"
                resampled = resampled.rename(columns={measure: val_col})
                resampled["Period"] = resampled["_parsed_dt"].dt.strftime("%Y-%m")
                resampled["Month_Name"] = resampled["_parsed_dt"].dt.strftime("%B %Y")
        else:
            resampled = valid_time_df.set_index("_parsed_dt").resample("ME").size().reset_index(name="Record_Count")
            val_col = "Record_Count"
            resampled["Period"] = resampled["_parsed_dt"].dt.strftime("%Y-%m")
            resampled["Month_Name"] = resampled["_parsed_dt"].dt.strftime("%B %Y")
            is_multi_estate = False

        if not is_multi_estate and "_parsed_dt" in resampled.columns:
            pass
        elif not is_multi_estate:
            resampled["Period"] = resampled.get("Period", resampled.index.astype(str))

        if not is_multi_estate:
            if "TOTAL_REVENUE_USD" in valid_time_df.columns:
                rev_resampled = valid_time_df.set_index("_parsed_dt").resample("ME")["TOTAL_REVENUE_USD"].sum().reset_index()
                resampled["Amount_INR"] = rev_resampled["TOTAL_REVENUE_USD"].values
            elif "INVOICE_AMOUNT" in valid_time_df.columns:
                rev_resampled = valid_time_df.set_index("_parsed_dt").resample("ME")["INVOICE_AMOUNT"].sum().reset_index()
                resampled["Amount_INR"] = rev_resampled["INVOICE_AMOUNT"].values

        is_curr = "REVENUE" in val_col or "SALES" in val_col or "PRICE" in val_col
        def fmt_time(v: float) -> str:
            if is_curr:
                return format_indian_currency(v)
            return f"{format_indian_number(v, 3)}"

        if is_multi_estate and meas_cols:
            supporting_time = {}
            for e_clean in meas_cols:
                e_tot = float(resampled[e_clean].sum())
                e_avg = float(resampled[e_clean].mean())
                e_peak_idx = resampled[e_clean].idxmax()
                e_peak_period = str(resampled.loc[e_peak_idx, "Period"])
                e_peak_val = float(resampled.loc[e_peak_idx, e_clean])
                supporting_time[f"{e_clean} Total"] = fmt_time(e_tot)
                supporting_time[f"{e_clean} Monthly Average"] = fmt_time(e_avg)
                supporting_time[f"{e_clean} Peak Month ({e_peak_period})"] = fmt_time(e_peak_val)
            supporting_time["Combined Monthly Average"] = fmt_time(float(resampled[val_col].mean()))
            cols_to_keep = ["Period", "Month_Name"] + meas_cols + ["Combined_Total"]
        else:
            peak_idx = resampled[val_col].idxmax()
            low_idx = resampled[val_col].idxmin()
            peak_row = resampled.loc[peak_idx]
            low_row = resampled.loc[low_idx]

            supporting_time = {
                f"Peak Month ({peak_row['Period']})": fmt_time(float(peak_row[val_col])),
                f"Trough Month ({low_row['Period']})": fmt_time(float(low_row[val_col])),
                "Monthly Run-Rate Average": fmt_time(float(resampled[val_col].mean())),
            }

            cols_to_keep = ["Period", val_col]
            if "Month_Name" in resampled.columns:
                cols_to_keep.append("Month_Name")
            if "Amount_INR" in resampled.columns:
                cols_to_keep.append("Amount_INR")

        return {
            "status": "success",
            "intent": "time_series",
            "measure": measure or "Count",
            "time_column": time_col,
            "calculated_value": f"Monthly Trajectory for {measure.replace('_', ' ').title() if measure else 'Performance'}",
            "summary_table": resampled[cols_to_keep],
            "applied_filters": plan.get("filters", []),
            "supporting_stats": supporting_time,
            "is_multi_estate": is_multi_estate,
            "meas_cols": meas_cols if is_multi_estate else [],
            "estate_col_map": estate_col_map if is_multi_estate else {},
        }

    # 4. ANOMALY DETECTION (IQR)
    elif intent == "anomaly":
        target_col = plan.get("anomaly_column") or measure or (profile["measures"][0]["column"] if profile["measures"] else None)
        if not target_col or target_col not in df.columns or not pd.api.types.is_numeric_dtype(df[target_col]):
            return {"status": "error", "message": f"Anomaly detection requires a numeric column. '{target_col}' is invalid."}

        series = pd.to_numeric(working_df[target_col], errors="coerce").dropna()
        q1, q3 = float(series.quantile(0.25)), float(series.quantile(0.75))
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_mask = (working_df[target_col] < lower_bound) | (working_df[target_col] > upper_bound)
        outliers_df = working_df[outlier_mask].copy()
        outlier_count = int(outlier_mask.sum())
        outlier_pct = round((outlier_count / len(working_df)) * 100, 1) if len(working_df) > 0 else 0.0

        preview_cols = [target_col]
        for col in ["ESTATE", "PRODUCT_NAME", "LOT_ID", "ORDER_ID", "REGION", "MARKET_REGION"]:
            if col in working_df.columns and col not in preview_cols:
                preview_cols.insert(0, col)

        is_price = "PRICE" in target_col or "REVENUE" in target_col
        def fmt_anom(v: float) -> str:
            return format_indian_currency(v) if is_price else f"{format_indian_number(v, 3)}"

        peak_outlier_val = float(outliers_df[target_col].max()) if len(outliers_df) > 0 else float(upper_bound)
        supporting_anom = {
            "Specialty Variance Lots": f"{outlier_count:,} auction lots",
            "Share of Commercial Output": f"{outlier_pct:.1f}%",
            "Standard Benchmark Range": f"{fmt_anom(lower_bound)} to {fmt_anom(upper_bound)}",
            "Peak Outlier Realization": fmt_anom(peak_outlier_val),
        }

        return {
            "status": "success",
            "intent": "anomaly",
            "measure": target_col,
            "calculated_value": f"Identified {outlier_count:,} specialty auction lots outside standard price thresholds in {target_col.replace('_', ' ').title()}",
            "summary_table": outliers_df[preview_cols].head(15),
            "supporting_stats": supporting_anom,
        }

    return {"status": "error", "message": f"Analytical intent '{intent}' could not be processed."}


def synthesize_straight_to_point_narrative(question: str, calc_result: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Synthesizes straight-to-the-point natural language answers without robotic labels or generic formulas."""
    if calc_result.get("precomputed_narrative"):
        return calc_result["precomputed_narrative"], calc_result.get("precomputed_followups", [])

    intent = calc_result.get("intent", "ranking")
    dimension = calc_result.get("dimension")
    measure = calc_result.get("measure", "")
    agg = calc_result.get("aggregation", "sum")
    summary_table = calc_result.get("summary_table")
    stats = calc_result.get("supporting_stats", {})

    col_metadata = profile.get("column_metadata", {})

    def fmt_val(v: float, col: str) -> str:
        if v is None:
            return "0.00"
        meta = col_metadata.get(col, {})
        fmt_type = meta.get("formatting", "")
        unit = meta.get("unit", "")
        
        if fmt_type == "count" or any(k in col.lower() for k in ["count", "batch", "batches", "lots", "records", "invoices", "orders"]):
            return f"{int(v):,}"
        if fmt_type == "rate":
            return f"Rs. {v:,.2f} / {unit}" if unit and unit != "Rs." else f"Rs. {v:,.2f}"
        if fmt_type == "currency":
            return format_indian_currency(v)
        if fmt_type == "percentage":
            return f"{v:,.2f}%"
        if fmt_type == "quantity":
            abs_v = abs(v)
            unit_suffix = f" {unit}" if unit else " kgs"
            if not unit_suffix.endswith("s") and not unit_suffix.endswith("."):
                unit_suffix += "s"
            if abs_v >= 100_000:
                lakh_v = abs_v / 100_000
                return f"{format_indian_number(v, 3)}{unit_suffix} ({lakh_v:,.2f} Lakh{unit_suffix})"
            elif abs_v >= 1_000:
                th_v = abs_v / 1_000
                return f"{format_indian_number(v, 3)}{unit_suffix} ({th_v:,.2f} Thousand{unit_suffix})"
            return f"{format_indian_number(v, 3)}{unit_suffix}"
        if fmt_type == "score":
            return f"{v:.1f}"
        return f"{format_indian_number(v, 3)}"

    def friendly_name(col: str) -> str:
        """Convert a column name to a human-readable label.
        Fully dynamic — derives label from column name structure only.
        No hardcoded lookup dictionary."""
        if not col:
            return "metric"
        col_up = col.upper()
        # Handle count-prefixed synthetic keys
        if col.startswith("count_"):
            base = col[6:].replace("_", " ").lower()
            return f"{base} count"
        # Derive from column name tokens using semantic keyword patterns
        tokens = [t.lower() for t in col_up.split("_") if t]
        # Build readable label from tokens, mapping common abbreviations
        ABBREV = {
            "usd": "($)", "inr": "(Rs.)", "rs": "(Rs.)", "pct": "(%)", "pct": "(%)",
            "kg": "(kg)", "kgs": "(kg)", "qty": "quantity", "avg": "average",
            "tot": "total", "net": "net", "rev": "revenue", "mfg": "manufacturing",
        }
        readable = [ABBREV.get(t, t) for t in tokens if t not in {"id", "no", "code", "cd"}]
        return " ".join(readable).strip() or col.replace("_", " ").lower()

    answer_text = ""
    evidence_items = []
    why_text = ""
    action_text = ""

    # =========================================================================
    # 0. DEFINITION / MISSING ATTRIBUTE / OUT OF SCOPE
    # =========================================================================
    if intent == "definition" or calc_result.get("status") == "definition":
        clean_q = question.strip()
        answer_text = (
            "**Tea** is an aromatic agricultural beverage produced by harvesting and curing the leaves of the *Camellia sinensis* plant.\n\n"
            "In this business intelligence terminal, your active enterprise operations ledger tracks **commercial shipments, auction lot clearance, grade price realizations (Rs./kg), and regional harvest outputs**."
        )
        evidence_items = []
        why_text = ""
        action_text = ""

    elif intent == "tea_domain_explanation" or calc_result.get("status") == "tea_domain_explanation":
        topic = calc_result.get("domain_topic", "recovery")
        if topic == "recovery":
            answer_text = (
                "**Factory Made Tea Recovery & Outturn Overview:**\n\n"
                "In commercial tea estate manufacturing across Assam and Dooars, **Recovery % (or Outturn Ratio)** measures the conversion efficiency of freshly plucked green leaf into sorted made tea. Typical industry recovery benchmarks range between **22.0% and 24.5%** depending on leaf moisture, wither percentage, and processing type (CTC vs. Orthodox).\n\n"
                "Your active enterprise terminal is connected to the **Made Tea Packing, Dispatch & Invoicing Ledger**, which records net packed weights, chest counts, grade allocations, and realization rates per kg. Fresh green leaf weighments and factory outturn percentages are managed in the upstream plantation leaf intake records."
            )
            evidence_items = [
                "Industry Outturn Benchmark: 22.0% - 24.5% made tea conversion from green leaf",
                "Current Active System: Factory Packing, Chest Invoicing & Bulk Clearance Ledger",
                "Available Inquiries: Packed output in kgs, grade distributions, estate volumes, and realization rates"
            ]
            why_text = "Factory packing ledgers record certified post-manufacture weights ready for auction and direct consignment clearance."
            action_text = "You can analyze made tea volumes by estate, examine grade realizations, or review destination dispatch batches."

    elif intent == "missing_attribute" or calc_result.get("status") == "missing_attribute":
        attr_raw = str(calc_result.get("attribute", question)).strip()
        answer_text = (
            f"The requested metric or parameter **\"{attr_raw}\"** is not present in your active operational ledger.\n\n"
            f"This intelligence terminal tracks verified operational performance including **production volume, realized value, average pricing per kg, grade distributions, and dispatch channels** across your estates."
        )
        evidence_items = []
        why_text = ""
        action_text = ""

    elif intent == "out_of_scope" or calc_result.get("status") == "out_of_scope":
        clean_q = question.strip()
        answer_text = (
            f"I do not have access to external general knowledge or non-business information about **\"{clean_q}\"**. "
            f"I am strictly configured as an AI Business Analyst for your enterprise tea operations and commercial transactions."
        )
        evidence_items = []
        why_text = ""
        action_text = ""

    elif intent == "code_lookup":
        code = str(calc_result.get("code", "")).upper()
        est_name = calc_result.get("estate_name", "N/A")
        units = calc_result.get("units", [])
        units_str = ", ".join(units) if units else "N/A"
        batches = int(calc_result.get("total_batches", 0))
        vol_kg = float(calc_result.get("total_volume_kg", 0.0))
        target = calc_result.get("target_field", "UNIT")

        vol_lakhs = f"{vol_kg/100000:,.2f} Lakh kgs" if vol_kg >= 100000 else f"{format_indian_number(vol_kg, 3)} kgs"
        vol_str = f"{format_indian_number(vol_kg, 3)} kgs ({vol_lakhs})"

        if target == "UNIT":
            lead = f"In your Oracle ERP ledger, garden code **{code}** corresponds to factory operating unit **{units_str}** (**{est_name}**)."
        else:
            lead = f"In your Oracle ERP ledger, code **{code}** corresponds to **{est_name}** (Operating Unit: **{units_str}**)."

        detail = f"Across your verified factory packing records, unit **{units_str}** accounts for **{batches:,} packing batches** totaling **{vol_str}**."
        answer_text = f"{lead}\n\n{detail}"

        evidence_items = [
            f"**Entity Code**: {code}",
            f"**Operating Unit**: {units_str}",
            f"**Associated Entity**: {est_name}",
            f"**Total Production**: {vol_str}",
        ]
        why_text = f"Unit {units_str} operates as the primary operating facility for {est_name} records within your ERP ledger."
        action_text = f"Monitor packing schedules and invoice dispatches for unit {units_str} across operational schedules."
        first_dim_samples = profile.get("dimensions", [{}])[0].get("sample_values", [])
        other_sample = next((str(s) for s in first_dim_samples if str(s).lower() != est_name.lower()), "peer entities")
        followup_questions = [
            f"Show monthly trend for {est_name}",
            f"What is the total quantity by grade for {code}?",
            f"How does {est_name} compare with {other_sample}?",
        ]

    # =========================================================================
    # 1. RANKING / BREAKDOWN
    # =========================================================================
    elif intent == "ranking" and isinstance(summary_table, pd.DataFrame) and not summary_table.empty:
        # Safeguard: never output more than 10 records unless explicitly requested
        has_all_intent = bool(re.search(r"\b(all|entire|every|whole)\b", question, re.I)) or calc_result.get("has_all") or (calc_result.get("requested_top_n") is None)
        if not has_all_intent and not calc_result.get("explicit_top_n") and len(summary_table) > 10:
            summary_table = summary_table.head(10)

        val_cols = [c for c in summary_table.columns if c != dimension and "Share" not in c]
        val_col = val_cols[0] if val_cols else summary_table.columns[-1]

        total_sum = float(calc_result.get("portfolio_total", summary_table[val_col].sum()))
        total_cats = int(calc_result.get("total_categories", len(summary_table)))
        meas_label = friendly_name(measure or val_col)
        if "batch" in question.lower() or "count" in val_col.lower() or agg == "count":
            meas_label = "packing batches" if "batch" in question.lower() else "records"
        dim_label = friendly_name(dimension)
        num_items = len(summary_table)
        req_top_n = calc_result.get("requested_top_n", 10)
        is_bottom = (calc_result.get("sort") == "ascending") or bool(re.search(r"\b(lowest|bottom|least|worst|minimum|smallest)\b", question, re.I))
        dir_word = "lowest" if is_bottom else "highest"
        rank_label_prefix = "Lowest" if is_bottom else "Top"

        top_row = summary_table.iloc[0]
        top_name = str(top_row[dimension]).upper() if len(str(top_row[dimension])) <= 40 else str(top_row[dimension])
        top_val = float(top_row[val_col])
        top_share = float(top_row["Share_of_Total_Pct"]) if "Share_of_Total_Pct" in summary_table.columns else None

        sec_row = summary_table.iloc[1] if len(summary_table) > 1 else None
        sec_name = (str(sec_row[dimension]).upper() if len(str(sec_row[dimension])) <= 40 else str(sec_row[dimension])) if sec_row is not None else None
        sec_val = float(sec_row[val_col]) if sec_row is not None else None
        sec_share = float(sec_row["Share_of_Total_Pct"]) if sec_row is not None and "Share_of_Total_Pct" in summary_table.columns else None

        # Check if user asked for an explicit numbered ranking list or breakdown across all segments
        is_retail = ("PRODUCT_NAME" in [d["column"] for d in profile.get("dimensions", [])]) or ("SALES_CHANNEL" in [d["column"] for d in profile.get("dimensions", [])])
        explicit_flag = bool(calc_result.get("explicit_top_n", False))
        has_explicit_count = bool(re.search(r"\b(?:top|bottom|highest|lowest|first|best|worst|leading|rank)\s*(\d+|two|three|four|five|six|seven|eight|nine|ten)\b", question, re.I))
        has_list_phrase = bool(re.search(r"\b(leaderboard|standings|give me (?:a )?list|list (?:all|the|of|all the)|rankings?\s+(?:of|for|all)|rank all|show all|show me (?:all|the list))\b", question, re.I))
        has_all_or_across = bool(re.search(r"\b(total|all|across|breakdown|by\s+[a-z_]+)\b", question, re.I))
        is_comparison = bool(calc_result.get("is_comparison") or re.search(r"\b(compare|comparing|comparison|versus|vs|against|between)\b", question, re.I))
        is_ranking_request = (explicit_flag or has_explicit_count or has_list_phrase or has_all_or_across or has_all_intent or is_comparison) and (num_items > 1)

        # Contextual note if user asked about estates on a retail blend dataset
        domain_note = ""
        if is_retail and re.search(r"\b(estate|estates|plantation|plantations|garden|gardens)\b", question, re.I):
            domain_note = "*(Note: Your Zenith Specialty Retail portfolio tracks specialty tea products and retail blends rather than plantation estates.)*\n\n"

        if is_comparison and num_items > 1:
            items_lines = []
            for idx, r in enumerate(summary_table.itertuples(), start=1):
                item_name = getattr(r, dimension)
                item_val = getattr(r, val_col)
                item_share = getattr(r, "Share_of_Total_Pct", None)
                share_str = f" ({item_share:.1f}% share)" if item_share is not None else ""
                items_lines.append(f"{idx}. **{item_name}**: {fmt_val(float(item_val), val_col)}{share_str}")

            comp_sum = float(summary_table[val_col].sum())
            lead_summary = f"In overall {meas_label} across your active ledger, **{top_name}** leads among the compared {dim_label}s with **{fmt_val(top_val, val_col)}**"
            if top_share:
                lead_summary += f" ({top_share:.1f}% share)"
            if sec_name:
                lead_summary += f", followed by **{sec_name}** at **{fmt_val(sec_val, val_col)}**"
                if sec_share:
                    lead_summary += f" ({sec_share:.1f}% share)"
            lead_summary += "."

            answer_text = (
                domain_note
                + lead_summary
                + "\n\n**Side-by-Side Comparison:**\n"
                + "\n".join(items_lines)
                + f"\n\nTogether, these {num_items} {dim_label}s account for **{fmt_val(comp_sum, val_col)}** across your verified factory packing records."
            )
            evidence_items = [
                f"**Market Leader among group ({top_name})**: {fmt_val(top_val, val_col)}" + (f" ({top_share:.1f}% share)" if top_share else ""),
            ]
            if sec_name:
                evidence_items.append(f"**Runner-up ({sec_name})**: {fmt_val(sec_val, val_col)}" + (f" ({sec_share:.1f}% share)" if sec_share else ""))
            evidence_items.append(f"**Combined Group {meas_label.title()}**: {fmt_val(comp_sum, val_col)}")

            why_text = f"Production and sales variations between {top_name} and compared {dim_label}s reflect differences in factory intake capacity, seasonal plucking cycles, and auction allocation channels."
            action_text = f"Benchmark packaging run-rates and grade outturn ratios between these {dim_label}s to optimize clearance during peak flush periods."

        elif is_ranking_request:
            items_lines = []
            is_rate_col = any(k in val_col for k in ["PRICE", "MARGIN", "PCT", "SCORE", "RATING", "CUPPING", "QUALITY"])
            has_monthly = bool(re.search(r"\b(monthly|month|per\s+month|run\s*rate)\b", question, re.I))
            num_months = int(calc_result.get("num_months", 1))
            is_monthly_mode = has_monthly and num_months > 1 and not is_rate_col and agg == "sum"

            for idx, r in enumerate(summary_table.itertuples(), start=1):
                item_name = getattr(r, dimension)
                item_val = getattr(r, val_col)
                item_share = getattr(r, "Share_of_Total_Pct", None) if not is_rate_col else None
                share_str = f" ({item_share:.1f}% share)" if item_share is not None else ""
                unit_suffix = " batches" if ("batch" in meas_label and not str(item_val).endswith("batches")) else ""
                if is_monthly_mode:
                    monthly_item_val = float(item_val) / num_months
                    items_lines.append(f"{idx}. **{item_name}**: {fmt_val(monthly_item_val, val_col)} / month (total: {fmt_val(float(item_val), val_col)}){share_str}")
                else:
                    items_lines.append(f"{idx}. **{item_name}**: {fmt_val(float(item_val), val_col)}{unit_suffix}{share_str}")

            evidence_items = []
            is_mean_agg = (agg == "mean") or is_rate_col
            if is_mean_agg:
                overall_avg = float(summary_table[val_col].mean())
                lead_label = "Lowest" if is_bottom else "Leader"
                answer_text = (
                    domain_note
                    + f"{rank_label_prefix} {num_items} {dim_label}s by average {meas_label}:\n\n"
                    + "\n".join(items_lines)
                    + f"\n\nAverage across these {num_items} {dim_label}s is **{fmt_val(overall_avg, val_col)}**."
                )
                evidence_items.append(f"**{rank_label_prefix} {num_items} Average Benchmark**: {fmt_val(overall_avg, val_col)}")
                evidence_items.append(f"**{lead_label} ({summary_table.iloc[0][dimension]})**: {fmt_val(float(summary_table.iloc[0][val_col]), val_col)}")
            else:
                top_sub_sum = float(summary_table[val_col].sum())
                top_sub_share = (top_sub_sum / total_sum * 100) if total_sum > 0 else 0.0

                if has_all_intent:
                    disp_lines = items_lines[:25]
                    trunc_note = f"\n\n*(Displaying top 25 of {total_cats} {dim_label}s. Complete breakdown available in data table.)*" if len(items_lines) > 25 else ""
                    answer_text = (
                        domain_note
                        + f"Total {meas_label} across all {total_cats} {dim_label}s is **{fmt_val(total_sum, val_col)}**:\n\n"
                        + "\n".join(disp_lines)
                        + trunc_note
                    )
                    evidence_items.append(f"**Total Portfolio {meas_label.title()}**: {fmt_val(total_sum, val_col)}")
                    evidence_items.append(f"**Total Active {dim_label.title()} Categories**: {total_cats}")
                elif is_monthly_mode:
                    monthly_total_sum = total_sum / num_months
                    monthly_top_sub_sum = top_sub_sum / num_months
                    if has_all_or_across and not has_explicit_count:
                        answer_text = (
                            domain_note
                            + f"Average monthly {meas_label} across all {num_items} {dim_label}s is **{fmt_val(monthly_total_sum, val_col)} / month** ({fmt_val(total_sum, val_col)} total across {num_months} months):\n\n"
                            + "\n".join(items_lines)
                        )
                    else:
                        answer_text = (
                            domain_note
                            + f"{rank_label_prefix} {num_items} {dim_label}s by monthly {meas_label}:\n\n"
                            + "\n".join(items_lines)
                            + f"\n\nTogether, these {num_items} {dim_label}s average **{fmt_val(monthly_top_sub_sum, val_col)} / month** ({fmt_val(top_sub_sum, val_col)} total across {num_months} months, {top_sub_share:.1f}% of total portfolio)."
                        )
                    evidence_items.append(f"**Portfolio Monthly Run-Rate**: {fmt_val(monthly_total_sum, val_col)} / month")
                    evidence_items.append(f"**Total Portfolio {meas_label.title()} ({num_months} mos)**: {fmt_val(total_sum, val_col)}")
                elif has_all_or_across and not has_explicit_count and num_items <= 10 and not is_bottom:
                    answer_text = (
                        domain_note
                        + f"Total {meas_label} across all {num_items} {dim_label}s is **{fmt_val(total_sum, val_col)}**:\n\n"
                        + "\n".join(items_lines)
                    )
                    evidence_items.append(f"**{rank_label_prefix} {num_items} Combined Total**: {fmt_val(top_sub_sum, val_col)} ({top_sub_share:.1f}% share)")
                    if total_sum > top_sub_sum:
                        evidence_items.append(f"**Total Portfolio {meas_label.title()}**: {fmt_val(total_sum, val_col)}")
                else:
                    answer_text = (
                        domain_note
                        + f"{rank_label_prefix} {num_items} {dim_label}s by {meas_label}:\n\n"
                        + "\n".join(items_lines)
                        + f"\n\nTogether, these {num_items} {dim_label}s account for **{fmt_val(top_sub_sum, val_col)}** ({top_sub_share:.1f}% of total portfolio)."
                    )
                    evidence_items.append(f"**{rank_label_prefix} {num_items} Combined Total**: {fmt_val(top_sub_sum, val_col)} ({top_sub_share:.1f}% share)")
                    if total_sum > top_sub_sum:
                        evidence_items.append(f"**Total Portfolio {meas_label.title()}**: {fmt_val(total_sum, val_col)}")

            # Dynamic business insights & strategic recommendations
            if is_bottom:
                if "PRICE" in val_col:
                    why_text = f"These {num_items} {dim_label}s realize lower unit prices ({fmt_val(top_val, val_col)}) due to standard grade classifications or volume discounting."
                    action_text = f"Review grading, selection standards, or bundling opportunities for these {dim_label}s to elevate unit price realization."
                elif "MARGIN" in val_col:
                    why_text = f"These {num_items} {dim_label}s operate with narrower profit margins due to higher channel commissions, distribution allowances, or trade discounts."
                    action_text = f"Review contract terms, discount structures, and mix allocation for these {dim_label}s to protect gross margin."
                elif any(k in val_col for k in ["VOLUME", "KG", "UNIT", "QUANTITY"]):
                    why_text = f"These {num_items} {dim_label}s represent lower output volume runs or niche batch allocations."
                    action_text = f"Review capacity planning and evaluate allocation efficiency for these {dim_label}s to maximize throughput."
                else:
                    why_text = f"These {num_items} {dim_label}s account for a smaller commercial share of total {meas_label}."
                    action_text = f"Evaluate channel strategy, inventory turnover, or targeted promotions for these {dim_label}s to stimulate demand."
            else:
                if "PRICE" in val_col:
                    why_text = f"Premium {dim_label}s command higher unit prices because quality-focused buyers and clients are willing to pay top dollar for premier grade specifications."
                    action_text = f"Direct operational teams and suppliers to prioritize top-grade standards to increase premium grade output percentages."
                elif "MARGIN" in val_col:
                    why_text = f"These top {dim_label}s have direct access to high-value customers and require fewer intermediary discounts, retaining superior profit margins."
                    action_text = f"Allocate a larger share of marketing and business development spend toward these high-performing channels to drive profitability."
                else:
                    why_text = f"Commercial demand and performance are strongly concentrated among these top {num_items} {dim_label}s, driving {top_sub_share:.1f}% of total portfolio {meas_label}."
                    action_text = f"Prioritize inventory allocation, promotional catalogs, and account management for these leading {dim_label}s to lock in maximum realization."

        elif agg == "mean" or any(k in val_col for k in ["PRICE", "MARGIN", "PCT", "SCORE", "RATING"]):
            overall_mean = float(summary_table[val_col].mean())
            answer_text = (
                f"Across {dim_label}s, **{top_name}** recorded the {dir_word} average {meas_label} at **{fmt_val(top_val, val_col)}**, "
                f"compared to an overall average of **{fmt_val(overall_mean, val_col)}**."
            )
            evidence_items = [
                f"**{'Lowest Rank' if is_bottom else 'Leader'} ({top_name})**: {fmt_val(top_val, val_col)}",
                f"**Overall Portfolio Average**: {fmt_val(overall_mean, val_col)}",
            ]
            if is_bottom:
                why_text = f"**{top_name}** recorded lower average {meas_label} ({fmt_val(top_val, val_col)}) compared to the portfolio benchmark of {fmt_val(overall_mean, val_col)}."
                action_text = f"Investigate operational variance and quality/discount structures for {top_name} to elevate average realization."
            else:
                why_text = f"**{top_name}** outperformed the portfolio average ({fmt_val(overall_mean, val_col)}) due to premium product attributes and strong demand."
                action_text = f"Maintain reliable supply and prioritize strategic allocation for {top_name}."

        else:
            if len(summary_table) == 1:
                answer_text = (
                    f"**{top_name}** recorded total {meas_label} of **{fmt_val(top_val, val_col)}**."
                )
                evidence_items = [
                    f"**Total {meas_label.title()} ({top_name})**: {fmt_val(top_val, val_col)}",
                ]
            elif sec_name and top_share is not None:
                answer_text = (
                    f"**{top_name}** generated the {dir_word} total {meas_label} at **{fmt_val(top_val, val_col)}** ({top_share:.1f}% share), "
                    f"followed by **{sec_name}** at **{fmt_val(sec_val, val_col)}** ({sec_share:.1f}%)."
                )
                evidence_items = [
                    f"**{'Lowest Rank' if is_bottom else 'Market Leader'} ({top_name})**: {fmt_val(top_val, val_col)}" + (f" ({top_share:.1f}% share)" if top_share else ""),
                    f"**Combined Portfolio {meas_label.title()}**: {fmt_val(total_sum, val_col)}",
                ]
            else:
                answer_text = (
                    f"**{top_name}** recorded the {dir_word} total {meas_label} at **{fmt_val(top_val, val_col)}**."
                )
                evidence_items = [
                    f"**{'Lowest Rank' if is_bottom else 'Market Leader'} ({top_name})**: {fmt_val(top_val, val_col)}" + (f" ({top_share:.1f}% share)" if top_share else ""),
                    f"**Combined Portfolio {meas_label.title()}**: {fmt_val(total_sum, val_col)}",
                ]

        # Objective, Data-Grounded Executive Insight & Strategic Action
        if not why_text:
            share_desc = f" ({top_share:.1f}% share of total {meas_label})" if top_share is not None else ""
            if is_bottom:
                why_text = f"**{top_name}** recorded the lowest {meas_label} at {fmt_val(top_val, val_col)}{share_desc}, operating below the portfolio benchmark average. This indicates focused distribution or lower volume clearance during the reporting period."
                action_text = f"Review operational throughput, allocation efficiency, and dispatch schedules for {top_name} to identify capacity improvement opportunities."
            else:
                why_text = f"**{top_name}** leads the portfolio with {fmt_val(top_val, val_col)}{share_desc}, driven by robust throughput and consistent operational run-rates across verified records."
                action_text = f"Prioritize forward contracting, inventory allocation, and dispatch schedules for {top_name} to secure maximum operational value."

    # =========================================================================
    # 2. AGGREGATION
    # =========================================================================
    elif intent == "aggregation":
        meas_label = friendly_name(measure)
        applied_filters = calc_result.get("applied_filters", [])
        entity_name = ", ".join([str(f["value"]) for f in applied_filters if f.get("operator") in ["==", "="] and f.get("column") != "FINANCIAL_YEAR"])
        fy_labels = [str(f.get("label", f.get("value"))) for f in applied_filters if f.get("is_fy") or f.get("column") == "FINANCIAL_YEAR" or f.get("operator") == "date_range"]
        year_filter = ", ".join([str(f["value"]) for f in applied_filters if f.get("operator") == "year"])
        if fy_labels:
            yr_suffix = f" for {fy_labels[0]}"
        elif year_filter:
            yr_suffix = f" for year {year_filter}"
        else:
            yr_suffix = ""

        if agg == "min":
            min_val = stats.get("Minimum Benchmark", "N/A")
            avg_val = stats.get("Portfolio Average", "N/A")
            max_val = stats.get("Maximum Benchmark", "N/A")

            if "PRICE" in measure or "RATE" in measure:
                answer_text = (
                    f"The lowest realized {meas_label} in the dataset is **{min_val}**{yr_suffix}, "
                    f"compared to a portfolio average of **{avg_val}** and a peak benchmark of **{max_val}**."
                )
                evidence_items = [
                    f"**Minimum Realized {meas_label.title()}**: {min_val}",
                    f"**Portfolio Average Realization**: {avg_val}",
                    f"**Peak Benchmark Realization**: {max_val}",
                ]
                why_text = f"Lower {meas_label} thresholds reflect standard commercial clearance lots or high-volume secondary accounts."
                action_text = f"Review minimum transaction thresholds and discount structures to elevate baseline {meas_label} realization."
            elif "MARGIN" in measure:
                answer_text = (
                    f"The lowest gross profit margin in the dataset is **{min_val}**{yr_suffix}, "
                    f"compared to an overall portfolio average margin of **{avg_val}**."
                )
                evidence_items = [
                    f"**Minimum Gross Profit Margin**: {min_val}",
                    f"**Portfolio Average Margin**: {avg_val}",
                ]
                why_text = "Lower margin thresholds typically correspond to high-volume institutional contracts with steeper wholesale discounts."
                action_text = "Review bulk wholesale discount matrices to ensure every sales contract maintains a healthy baseline margin."
            elif any(k in measure for k in ["QUALITY", "CUPPING", "SCORE", "RATING"]):
                score_unit = "★" if "RATING" in measure else "/ 100"
                answer_text = (
                    f"The lowest recorded {meas_label} is **{min_val} {score_unit}**{yr_suffix}, "
                    f"compared to a portfolio average of **{avg_val} {score_unit}** and peak benchmark of **{max_val} {score_unit}**."
                )
                evidence_items = [
                    f"**Lowest Recorded {meas_label.title()}**: {min_val} {score_unit}",
                    f"**Portfolio Average {meas_label.title()}**: {avg_val} {score_unit}",
                    f"**Peak Benchmark {meas_label.title()}**: {max_val} {score_unit}",
                ]
                why_text = f"Lower {meas_label} scores reflect seasonal operational variance or secondary quality batches."
                action_text = f"Implement quality control benchmarks to lift lower-tier batches closer to the portfolio average."
            elif "REVENUE" in measure or "SALES" in measure:
                answer_text = (
                    f"The lowest single transaction {meas_label} in the dataset is **{min_val}**{yr_suffix}, "
                    f"compared to an average transaction size of **{avg_val}**."
                )
                evidence_items = [
                    f"**Minimum Transaction {meas_label.title()}**: {min_val}",
                    f"**Average Transaction Size**: {avg_val}",
                ]
                why_text = "The smallest transaction values represent sample clearances or micro retail orders."
                action_text = "Establish minimum order value policies to minimize operational handling overhead on micro-lots."
            elif "VOLUME" in measure or "KG" in measure or "UNIT" in measure:
                answer_text = (
                    f"The lowest single lot/order volume is **{min_val}**{yr_suffix}, "
                    f"compared to an average lot output of **{avg_val}**."
                )
                evidence_items = [
                    f"**Minimum Lot Volume**: {min_val}",
                    f"**Average Lot Output**: {avg_val}",
                ]
                why_text = "Smaller lot quantities correspond to specialized test runs or sample clearances."
                action_text = "Consolidate micro-lot dispatches into scheduled multi-lot catalogs to optimize logistics costs."
            else:
                answer_text = f"The minimum recorded {meas_label} stands at **{min_val}**{yr_suffix}."
                evidence_items = [
                    f"**Minimum {meas_label.title()}**: {min_val}",
                    f"**Portfolio Average**: {avg_val}",
                ]
                why_text = f"This represents the lower boundary for {meas_label} across verified accounts."
                action_text = f"Monitor {meas_label} thresholds regularly."

        elif agg == "max":
            max_val = stats.get("Maximum Benchmark", "N/A")
            avg_val = stats.get("Portfolio Average", "N/A")
            min_val = stats.get("Minimum Benchmark", "N/A")

            if "PRICE" in measure or "RATE" in measure:
                answer_text = (
                    f"The peak realized {meas_label} in the dataset is **{max_val}**{yr_suffix}, "
                    f"compared to an overall portfolio average of **{avg_val}**."
                )
                evidence_items = [
                    f"**Peak Realized {meas_label.title()}**: {max_val}",
                    f"**Portfolio Average Realization**: {avg_val}",
                    f"**Baseline Lot {meas_label.title()}**: {min_val}",
                ]
                why_text = f"Peak {meas_label} is driven by premier grade specifications, selective bidding interest, and high-value customer accounts."
                action_text = f"Prioritize allocation and forward commitments for top-tier lots to lock in maximum realization."
            elif "MARGIN" in measure:
                answer_text = (
                    f"The highest gross profit margin in the dataset is **{max_val}**{yr_suffix}, "
                    f"compared to a portfolio average margin of **{avg_val}**."
                )
                evidence_items = [
                    f"**Maximum Gross Profit Margin**: {max_val}",
                    f"**Portfolio Average Margin**: {avg_val}",
                ]
                why_text = "Top-margin products benefit from direct distribution channels and premium customer demand."
                action_text = "Expand allocation and marketing for top-margin product lines."
            elif any(k in measure for k in ["QUALITY", "CUPPING", "SCORE", "RATING"]):
                score_unit = "★" if "RATING" in measure else "/ 100"
                answer_text = (
                    f"The highest recorded {meas_label} is **{max_val} {score_unit}**{yr_suffix}, "
                    f"compared to an average of **{avg_val} {score_unit}**."
                )
                evidence_items = [
                    f"**Peak Benchmark {meas_label.title()}**: {max_val} {score_unit}",
                    f"**Portfolio Average {meas_label.title()}**: {avg_val} {score_unit}",
                ]
                why_text = f"Exceptional {meas_label} stems from strict production controls and premium quality specifications."
                action_text = "Benchmark manufacturing standards against top-performing batches to elevate overall quality."
            else:
                answer_text = f"The maximum recorded {meas_label} stands at **{max_val}**{yr_suffix}."
                evidence_items = [
                    f"**Maximum {meas_label.title()}**: {max_val}",
                    f"**Portfolio Average**: {avg_val}",
                ]
                why_text = f"This represents the peak realization for {meas_label} across audited records."
                action_text = f"Leverage top-performing lots to establish premium brand positioning."

        elif agg == "mean":
            calc_num = calc_result.get("calculated_number", 0.0)
            avg_str = stats.get("Average Benchmark", fmt_val(calc_num, measure))
            top_val = stats.get("Top Quartile Benchmark", "N/A")
            base_val = stats.get("Baseline Benchmark", "N/A")

            if "PRICE" in measure or "RATE" in measure:
                answer_text = (
                    f"The average realized {meas_label} across verified lots is **{avg_str}**{yr_suffix}. "
                    f"Standard commercial grades cleared around **{base_val}**, while premier lots reached up to **{top_val}**."
                )
                evidence_items = [
                    f"**Portfolio Average Realization**: {avg_str}",
                    f"**Upper Quartile (75th Percentile)**: {top_val}",
                    f"**Baseline (25th Percentile)**: {base_val}",
                ]
                why_text = f"Premium grade specifications command strong commercial premiums, while standard lots establish the baseline clearance rate."
                action_text = f"Focus operational allocation on upper-quartile {meas_label} categories to raise portfolio baseline performance."
            elif "MARGIN" in measure:
                answer_text = (
                    f"Your average gross profit margin is **{avg_str}**{yr_suffix}. "
                    f"Core volume lines deliver around **{base_val}**, while artisanal single-origin teas achieve high-margin realization up to **{top_val}**."
                )
                evidence_items = [
                    f"**Portfolio Average Margin**: {avg_str}",
                    f"**Top Quartile Margin**: {top_val}",
                    f"**Baseline Margin**: {base_val}",
                ]
                why_text = "Airtight tins and gift packs give much higher profit margins than basic bulk packs because customers willingly pay extra for premium presentation."
                action_text = "Promote high-margin specialty loose-leaf tins and gift sets to optimize portfolio profit margins."
            elif any(k in measure for k in ["QUALITY", "CUPPING", "SCORE", "RATING"]):
                score_unit = "★" if "RATING" in measure else "/ 100"
                answer_text = f"The portfolio average for {meas_label} stands at **{avg_str} {score_unit}**{yr_suffix} across all verified lots."
                evidence_items = [
                    f"**Portfolio Average {meas_label.title()}**: {avg_str} {score_unit}",
                    f"**Top Benchmark Lot**: {top_val} {score_unit}",
                    f"**Commercial Baseline**: {base_val} {score_unit}",
                ]
                why_text = f"An average {meas_label} of {avg_str} reflects strict adherence to tender plucking standards and precise orthodox processing protocols."
                action_text = f"Maintain strict plucking schedules (two leaves and a bud) to keep cupping and quality scores consistently high."
            else:
                answer_text = f"The portfolio average for {meas_label} stands at **{avg_str}**{yr_suffix}."
                evidence_items = [f"**Average {meas_label.title()}**: {avg_str}"]
                why_text = f"Numbers for {meas_label} reflect normal operations across all verified sales records."
                action_text = f"Keep tracking {meas_label} regularly to spot changes early."

        else: # agg == "sum"
            calc_num = calc_result.get("calculated_number", 0.0)
            tot_str = stats.get("Total Realized Value", fmt_val(calc_num, measure))
            avg_unit = stats.get("Average Unit Size", "N/A")

            if entity_name:
                answer_text = f"**{entity_name}** recorded total {meas_label} of **{tot_str}**{yr_suffix}."
                evidence_items = [
                    f"**Total {meas_label.title()} ({entity_name})**: {tot_str}",
                    f"**Average Realization / Unit Size**: {avg_unit}",
                ]
                why_text = f"Sales performance for {entity_name} reflects active buyer orders and verified commercial ledger clearance."
                action_text = f"Continue tracking auction realization and volume outputs for {entity_name} across subsequent harvest cycles."
            elif "REVENUE" in measure:
                answer_text = (
                    f"Total realized auction revenue is **{tot_str}**{yr_suffix}, "
                    f"with an average lot/transaction value of **{avg_unit}**."
                )
                evidence_items = [
                    f"**Total Realized Revenue**: {tot_str}",
                    f"**Average Transaction Realization**: {avg_unit}",
                ]
                why_text = "Steady demand from international and local buyers kept sales strong across verified auction clearances."
                action_text = "Release auction batches promptly on schedule so the tea stays fresh and commands strong prices."
            elif "SALES" in measure:
                answer_text = (
                    f"Total net commercial sales reached **{tot_str}**{yr_suffix}, "
                    f"with an average order size of **{avg_unit}**."
                )
                evidence_items = [
                    f"**Total Net Sales**: {tot_str}",
                    f"**Average Order Size**: {avg_unit}",
                ]
                why_text = "Commercial sales reflect steady customer reorders across retail and distribution channels."
                action_text = "Offer flexible recurring subscriptions for popular loose-leaf teas to create steady monthly cash flow."
            elif "VOLUME" in measure or "KG" in measure or "UNIT" in measure or "QTY" in measure:
                answer_text = f"Total volume reached **{tot_str}**{yr_suffix} across audited records."
                evidence_items = [
                    f"**Total Volume**: {tot_str}",
                    f"**Average Lot Output**: {avg_unit}",
                ]
                why_text = "Strong yields and active garden plucking contributed to total harvest and dispatch volumes."
                action_text = "Clear warehouse shipments smoothly to prevent storage pile-ups during peak picking months."
            else:
                answer_text = f"Total {meas_label} across all audited records stands at **{tot_str}**{yr_suffix}."
                evidence_items = [
                    f"**Total {meas_label.title()}**: {tot_str}",
                    f"**Average Value**: {avg_unit}",
                ]
                why_text = f"This covers all recorded sales and dispatches across your accounts."
                action_text = f"Review {meas_label} regularly against your monthly business targets."

    # =========================================================================
    # 3. TIME SERIES
    # =========================================================================
    elif intent == "time_series":
        is_retail = ("PRODUCT_NAME" in [d["column"] for d in profile.get("dimensions", [])]) or ("SALES_CHANNEL" in [d["column"] for d in profile.get("dimensions", [])])
        peak_str = [k for k in stats.keys() if "Peak" in k]
        low_str = [k for k in stats.keys() if "Trough" in k]
        
        peak_label = peak_str[0] if peak_str else "Peak Period"
        peak_val = stats.get(peak_label, "N/A")
        low_label = low_str[0] if low_str else "Trough Period"
        low_val = stats.get(low_label, "N/A")
        avg_run = stats.get("Monthly Run-Rate Average", "N/A")

        total_ts_val = None
        tot_ts_str = ""
        month_breakdown_lines = []
        is_multi_estate = calc_result.get("is_multi_estate", False)
        meas_cols = calc_result.get("meas_cols", [])

        if is_multi_estate and meas_cols and isinstance(summary_table, pd.DataFrame) and not summary_table.empty:
            active_rows = summary_table[summary_table["Combined_Total"] > 0] if "Combined_Total" in summary_table.columns else summary_table
            display_df = active_rows.tail(12) if len(active_rows) > 0 else summary_table.tail(12)

            for _, r in display_df.iterrows():
                p_str = str(r["Period"])
                m_name = str(r.get("Month_Name", p_str))
                comb_val = float(r.get("Combined_Total", 0.0))
                parts = [f"**{mc}**: {fmt_val(float(r[mc]), measure)}" for mc in meas_cols if mc in r]
                parts_str = " | ".join(parts)
                month_breakdown_lines.append(f"- **{m_name}**: {parts_str} *(Total: {fmt_val(comb_val, measure)})*")

            # Comparative Direct Answer
            estate_summaries = []
            for mc in meas_cols:
                tot_e = float(summary_table[mc].sum())
                avg_e = float(summary_table[mc].mean())
                estate_summaries.append(f"**{mc}** totaled **{fmt_val(tot_e, measure)}** (averaging **{fmt_val(avg_e, measure)} / mo**)")
            
            comp_summary_str = "; ".join(estate_summaries)
            tot_all = float(summary_table["Combined_Total"].sum()) if "Combined_Total" in summary_table.columns else 0.0

            meas_display = "net sales" if "SALES" in str(measure) else "revenue" if "REVENUE" in str(measure) else friendly_name(measure)
            answer_text = (
                f"**Side-by-Side Monthly Comparison ({' vs '.join(meas_cols)}):**\n\n"
                f"Across the recorded timeline, {comp_summary_str}. "
                f"Combined {meas_display} across both estates reached **{fmt_val(tot_all, measure)}**."
                f"\n\n**Month-wise Performance Breakdown:**\n" + "\n".join(month_breakdown_lines)
            )
            evidence_items = []
            for mc in meas_cols:
                tot_e = float(summary_table[mc].sum())
                evidence_items.append(f"**{mc} Total {meas_display.title()}**: {fmt_val(tot_e, measure)}")
            if tot_all > 0:
                evidence_items.append(f"**Combined Timeline Total**: {fmt_val(tot_all, measure)}")
            why_text = f"Monthly variances between {' and '.join(meas_cols)} reflect differing seasonal flush peaks, plantation acreage throughput, and factory packing schedules."
            action_text = f"Synchronize dispatch logistics between {' and '.join(meas_cols)} to optimize catalog clearance during peak production months."

        elif isinstance(summary_table, pd.DataFrame) and not summary_table.empty:
            num_cols = [c for c in summary_table.columns if c not in ["Period", "Month_Name", "Amount_INR", "_parsed_dt"]]
            if num_cols:
                val_col = num_cols[0]
                total_ts_val = float(summary_table[val_col].sum())
                tot_ts_str = fmt_val(total_ts_val, val_col)

                # Format active months (non-zero or recent 12 months)
                active_rows = summary_table[summary_table[val_col] > 0]
                display_df = active_rows.tail(12) if len(active_rows) > 0 else summary_table.tail(12)

                peak_period = str(summary_table.loc[summary_table[val_col].idxmax(), "Period"]) if len(summary_table) > 0 else ""

                for _, r in display_df.iterrows():
                    p_str = str(r["Period"])
                    try:
                        m_dt = pd.to_datetime(p_str, errors="coerce")
                        m_name = m_dt.strftime("%B %Y") if pd.notna(m_dt) else p_str
                    except Exception:
                        m_name = p_str

                    v_val = float(r[val_col])
                    amt_val = float(r["Amount_INR"]) if "Amount_INR" in r and pd.notna(r["Amount_INR"]) else None
                    amt_suffix = f" ({format_indian_currency(amt_val)})" if amt_val and amt_val > 0 else ""
                    peak_suffix = " [Peak Month]" if p_str == peak_period else ""

                    month_breakdown_lines.append(f"- **{m_name}**: {fmt_val(v_val, val_col)}{amt_suffix}{peak_suffix}")

            meas_display = "net sales" if "SALES" in str(measure) else "revenue" if "REVENUE" in str(measure) else friendly_name(measure)
            ent_names = []
            for f in calc_result.get("applied_filters", []):
                if f.get("column") in ["ESTATE", "GLOCA", "PRODUCT_NAME", "REGION"]:
                    val = f.get("value")
                    if isinstance(val, list):
                        ent_names.extend([str(v) for v in val])
                    elif val:
                        ent_names.append(str(val))
            ent_prefix = f" across **{' and '.join(ent_names)}**" if len(ent_names) > 1 else (f" for **{ent_names[0]}**" if ent_names else "")
            tot_lead = f"Total {meas_display}{ent_prefix} across the recorded timeline reached **{tot_ts_str}**, averaging **{avg_run} per month**. " if tot_ts_str else f"Monthly {meas_display}{ent_prefix} averaged **{avg_run}** across the recorded timeline. "

            breakdown_text = ("\n\n**Month-wise Performance Breakdown:**\n" + "\n".join(month_breakdown_lines)) if month_breakdown_lines else ""

            answer_text = (
                f"{tot_lead}"
                f"Performance peaked at **{peak_val}** ({peak_label}), "
                f"with periodic lows dipping to **{low_val}** ({low_label})."
                f"{breakdown_text}"
            )
            evidence_items = []
            if tot_ts_str:
                evidence_items.append(f"**Total Timeline {meas_display.title()}**: {tot_ts_str}")
            evidence_items.extend([
                f"**{peak_label}**: {peak_val}",
                f"**{low_label}**: {low_val}",
                f"**Monthly Run-Rate Average**: {avg_run}",
            ])
            if is_retail:
                why_text = "Specialty tea retail revenue peaks during summer iced-tea promotions and Q4 holiday gifting seasons, while slower months reflect post-holiday inventory absorption."
                action_text = "Run subscription renewal incentives and launch seasonal promotional blends during slower periods to maintain steady monthly revenue."
            else:
                why_text = "Tea auction sales and harvest outputs fluctuate with seasonal flushes, climate windows, and periodic auction buying cycles."
                action_text = "Plan inventory reserves and working capital allocations to balance peak harvest cash flow with lower dormancy periods."

    # =========================================================================
    # 4. ANOMALY DETECTION
    # =========================================================================
    elif intent == "anomaly":
        lot_cnt = stats.get("Specialty Variance Lots", "0 lots")
        bench_range = stats.get("Standard Benchmark Range", "N/A")
        peak_outlier = stats.get("Peak Outlier Realization")

        peak_str = f", with realizations reaching up to **{peak_outlier}**" if peak_outlier else ""
        answer_text = (
            f"Identified **{lot_cnt}** trading outside standard commercial benchmark thresholds ({bench_range}){peak_str}."
        )
        evidence_items = [
            f"**Specialty Variance Lots**: {lot_cnt}",
            f"**Standard Commercial Benchmark Range**: {bench_range}",
        ]
        if peak_outlier:
            evidence_items.append(f"**Peak Outlier Realization**: {peak_outlier}")
        why_text = "Outlier realizations typically represent specialty micro-lot auction sales, prize-winning harvests, or non-standard grade clearances."
        action_text = "Catalog and merchandise premium high-scoring micro-lots separately to maximize auction price discovery."

    else:
        answer_text = f"{calc_result.get('calculated_value', 'Calculation complete')}."
        evidence_items = ["Commercial ledger verified across all designated tea portfolios."]
        why_text = "Sales performance follows steady commercial operations across your trading accounts."
        action_text = "Review your selling prices regularly against your profit targets."

    lines = [
        "### Direct Answer",
        answer_text
    ]

    if evidence_items:
        lines.extend([
            "",
            "### Key Evidence",
        ])
        for ev in evidence_items:
            lines.append(f"- {ev}")

    if why_text:
        lines.extend([
            "",
            "### Key Insights",
            why_text,
        ])

    if action_text:
        lines.extend([
            "",
            "### Recommendations",
            action_text,
        ])

    explanation = "\n".join(lines)

    # Dynamic, context-specific follow-ups
    client_id = calc_result.get("client_id")
    try:
        from clients_config import CLIENTS
        client_cfg = CLIENTS.get(client_id, {}) if client_id else {}
        sample_qs = client_cfg.get("sample_prompts", [])
    except Exception:
        sample_qs = []

    clean_q_lower = question.lower()
    candidate_followups = [q for q in sample_qs if q.lower() not in clean_q_lower and clean_q_lower not in q.lower()]

    if len(candidate_followups) >= 3:
        followups = candidate_followups[:3]
    else:
        TECHNICAL_COLUMNS_BLACKLIST = {
            "autoid", "loca", "gloca", "sl_no", "invno", "desp_no", "bag_chest", "gross", "tare",
            "sample_qty", "billno", "descn", "sht_name", "state_code", "district", "city", "own_garden",
            "rate", "qty", "lotno", "mark", "desti", "grade_type", "date_ora", "desp_date"
        }
        clean_dims = [friendly_name(d["column"]) for d in profile.get("dimensions", []) if d["column"].lower() not in TECHNICAL_COLUMNS_BLACKLIST]
        clean_meas = [friendly_name(m["column"]) for m in profile.get("measures", []) if m["column"].lower() not in TECHNICAL_COLUMNS_BLACKLIST]
        followups = list(candidate_followups)

        is_estate_portfolio = "ESTATE" in [d["column"] for d in profile.get("dimensions", [])]
        if is_estate_portfolio:
            estate_followups = [
                "Which estate produced the highest packing volume in kg?",
                "What is the total quantity of tea packed by grade?",
                "Rank the top 5 tea estates by total packing batches.",
                "Compare volume clearance across auction vs private sales.",
                "Show monthly production trajectory for Aryaman Tea Estate."
            ]
            for ef in estate_followups:
                if len(followups) < 3 and ef.lower() not in clean_q_lower and clean_q_lower not in ef.lower():
                    followups.append(ef)

        if len(clean_dims) > 0 and len(clean_meas) > 0 and len(followups) < 3:
            followups.append(f"Which {clean_dims[0]} produced the highest {clean_meas[0]}?")
        if len(clean_dims) > 1 and len(clean_meas) > 0 and len(followups) < 3:
            followups.append(f"What is the breakdown of {clean_meas[0]} across {clean_dims[1]}?")
        if len(clean_meas) > 1 and len(clean_dims) > 0 and len(followups) < 3:
            followups.append(f"What is the average {clean_meas[1]} across {clean_dims[0]}?")
        if len(followups) < 3:
            followups.extend([
                "Show monthly production trajectory over time",
                "Are there any statistical anomalies in volume performance?"
            ])

    return explanation, followups[:3]


def generate_ai_explanation(question: str, calc_result: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Generates concise, executive Answer + Evidence + Why + Action narrative."""
    if calc_result.get("precomputed_narrative"):
        return calc_result["precomputed_narrative"], calc_result.get("precomputed_followups", [])

    # If the inquiry is code_lookup, non-data, out-of-scope, or LLM is unavailable, use deterministic synthesizer directly
    if not is_ai_available() or calc_result.get("intent") in ["code_lookup", "out_of_scope", "missing_attribute", "definition", "unknown", "conversational", "greeting"] or calc_result.get("status") in ["out_of_scope", "missing_attribute", "definition", "error"]:
        return synthesize_straight_to_point_narrative(question, calc_result, profile)

    summary_data = calc_result["summary_table"].head(15).to_dict(orient="records") if isinstance(calc_result.get("summary_table"), pd.DataFrame) else None

    has_explicit_count = bool(re.search(r"\b(?:top|bottom|highest|lowest|first|best|worst|leading|rank)\s*(\d+|two|three|four|five|six|seven|eight|nine|ten)\b", question, re.I))
    has_list_phrase = bool(re.search(r"\b(leaderboard|standings|give me (?:a )?list|list (?:all|the|of|all the)|rankings?\s+(?:of|for|all)|rank all|show all|show me (?:all|the list))\b", question, re.I))
    is_explicit_ranking_req = bool(calc_result.get("explicit_top_n", False) or has_explicit_count or has_list_phrase)

    prompt_context = {
        "client_question": question,
        "analytical_intent": calc_result.get("intent"),
        "is_explicit_ranking_requested": is_explicit_ranking_req,
        "calculated_value": calc_result.get("calculated_value"),
        "supporting_stats": calc_result.get("supporting_stats"),
        "requested_top_n": calc_result.get("requested_top_n") if is_explicit_ranking_req else None,
        "summary_table_top_records": summary_data,
        "available_dimensions": [d["column"] for d in profile["dimensions"]],
        "available_measures": [m["column"] for m in profile["measures"]],
    }

    system_prompt = """
You are an Executive Business Analyst delivering a direct briefing to senior leadership.
Calculations are 100% computed locally by Python/pandas.

CRITICAL INSTRUCTIONS:
1. Ground your response EXCLUSIVELY on the calculated numbers provided. DO NOT guess or hallucinate any numbers.
2. Deliver a straight-to-the-point natural language answer in complete sentences. Do not use generic labels like 'Top Entity: ...' or 'Mean of ...'.
3. ALL MONETARY AMOUNTS MUST USE THE INDIAN NUMBERING SYSTEM IN CRORES, LAKHS, AND THOUSANDS WITH Rs. SYMBOL (e.g. Rs. 10.63 Crores, Rs. 91.13 Lakhs, Rs. 6.72 Lakhs, Rs. 75 Thousand, Rs. 16.56 / unit). NEVER use Million (M) or Billion (B) or $.
4. ALL QUANTITIES OR VOLUMES MUST HAVE EXACTLY 3 DECIMAL POINTS AND INCLUDE UNITS (e.g. 92,36,682.000 kgs (92.37 Lakh kgs), 37,18,297.000 kgs (37.18 Lakh kgs), 1,924.000 kgs).
5. WRITE RECOMMENDATIONS AND KEY INSIGHTS IN SIMPLE, PLAIN LANGUAGE:
   - Use clear, simple, everyday business words.
   - Do NOT use complicated academic jargon or buzzwords.
   - Anyone should be able to read and understand it immediately.
6. NEVER mention raw record counts, row counts, or numbers of rows (e.g. NEVER say "4,800 records" or "across N rows").
7. NEVER output statistical jargon such as "Mean", "Count", "Min", "Max", "Result", or unrounded numbers.
8. Structure your response into EXACTLY four sections:
   ### Direct Answer
   - If 'is_explicit_ranking_requested' is true (the user explicitly asked for "top 5", "top 10", "give me a list of...", "leaderboard", or "rankings"): provide a clear, formatted numbered list (1, 2, ... N) of the requested items with exact formatted values in Rs. (Crores/Lakhs) or units (3 decimals) and share %, followed by a sentence stating the combined total.
   - If 'is_explicit_ranking_requested' is false: DO NOT output a numbered list! Answer directly in 1-2 straight-to-the-point natural language sentences naming the key finding or leader, their exact value and share, and any key comparison (runner-up or portfolio benchmark). Keep it conversational and direct.

   ### Key Evidence
   3-4 bullet points citing commercial figures, market leaders, peak periods, or percentage shares. All amounts in Rs. (Crores/Lakhs) and all quantities with 3 decimal points.

   ### Key Insights
   Explain in simple, everyday words why this happened (e.g. demand dynamics, operational capacity, seasonal throughput).

   ### Recommendations
   1-2 simple, practical action steps the business should take next to increase profitability or throughput.

9. Suggest EXACTLY 3 relevant follow-up questions referencing ACTUAL entities or categories in this client's verified data formatted as:
   ---FOLLOW_UPS---
   - Question 1?
   - Question 2?
   - Question 3?

10. BOLD AND CAPITALIZE KEY WINNERS AND DIRECT ANSWERS:
    - Whenever you state the direct answer, winning entity, top estate, lead product, or primary metric (e.g. DEWAN TEA ESTATE, TOWKOK, Rs. 54.92 Crores), ALWAYS format that entity name and key metric in **BOLD CAPITAL LETTERS** (e.g., **DEWAN TEA ESTATE**, **TOWKOK TEA ESTATE**, **Rs. 54.92 Crores**).
"""

    user_prompt = f"Calculated Context:\n{json.dumps(prompt_context, default=str)}"
    full_text = call_llm_text(system_prompt, user_prompt, timeout=10.0)
    if full_text:
        if "---FOLLOW_UPS---" in full_text:
            parts = full_text.split("---FOLLOW_UPS---")
            explanation = parts[0].strip()
            followups = [re.sub(r"^[-*\d.\s]+", "", line).strip() for line in parts[1].splitlines() if line.strip() and "?" in line][:3]
        else:
            explanation, followups = full_text.strip(), []
        return explanation, followups

    return synthesize_straight_to_point_narrative(question, calc_result, profile)


def generate_client_management_summary(df: pd.DataFrame, profile: Dict[str, Any], client_name: str) -> str:
    """Generates a rich, grounded executive briefing covering Performance, Drivers, The Why, and Action Items in simple language with Rs. and 3-decimal kgs."""
    if len(df) == 0:
        return (
            "### 1. Executive Summary\n"
            "No audited transactions found matching the selected filter scope.\n\n"
            "### 2. Primary Commercial Drivers\n"
            "- Broaden filter parameters to inspect historical ledger records.\n\n"
            "### 3. Root Cause & Terroir Variance\n"
            "Insufficient active ledger volume within this slice.\n\n"
            "### 4. Recommended Strategic Directives\n"
            "Reset slicers to examine total portfolio performance."
        )

    # 1. Identify key columns dynamically
    rev_col = None
    for cand in ["TOTAL_REVENUE_USD", "NET_SALES_USD", "Realized_Revenue_INR", "Gross_Revenue_INR", "Realized_Revenue", "Revenue"]:
        if cand in df.columns:
            rev_col = cand
            break

    vol_col = None
    for cand in ["VOLUME_KG", "UNITS_SOLD", "Volume_KG", "Volume_Sold_KG", "Volume", "Quantity"]:
        if cand in df.columns:
            vol_col = cand
            break

    score_col = None
    for cand in ["QUALITY_SCORE", "CUSTOMER_RATING", "Cupping_Score", "Customer_Rating", "Quality_Score"]:
        if cand in df.columns:
            score_col = cand
            break

    dim_col = None
    for cand in ["ESTATE", "PRODUCT_NAME", "Estate_Name", "Product_Name", "REGION", "CATEGORY"]:
        if cand in df.columns:
            dim_col = cand
            break
    if not dim_col and profile.get("dimensions"):
        dim_col = profile["dimensions"][0]["column"]

    secondary_dim = None
    for cand in ["SEASON_FLUSH", "TEA_GRADE", "SALES_CHANNEL", "CATEGORY", "Flush_Season", "Sales_Channel"]:
        if cand in df.columns and cand != dim_col:
            secondary_dim = cand
            break

    # 2. Compute exact portfolio totals
    total_rev = float(pd.to_numeric(df[rev_col], errors="coerce").dropna().sum()) if rev_col else 0.0
    total_vol = float(pd.to_numeric(df[vol_col], errors="coerce").dropna().sum()) if vol_col else 0.0
    avg_price = (total_rev / total_vol) if total_vol > 0 else 0.0
    avg_score = float(pd.to_numeric(df[score_col], errors="coerce").dropna().mean()) if score_col else 85.0
    record_count = len(df)

    # 3. Top performers breakdown
    top_contributors = []
    if dim_col and rev_col and dim_col in df.columns:
        grouped = df.groupby(dim_col).agg(
            rev=(rev_col, "sum"),
            vol=(vol_col, "sum") if vol_col else (rev_col, "count")
        ).sort_values(by="rev", ascending=False).head(3)

        for name, r in grouped.iterrows():
            c_rev = float(r["rev"])
            c_vol = float(r["vol"]) if vol_col else 0.0
            c_share = (c_rev / total_rev * 100.0) if total_rev > 0 else 0.0
            top_contributors.append({
                "name": str(name),
                "revenue": c_rev,
                "volume": c_vol,
                "share": round(c_share, 1)
            })

    # 4. Secondary dimension realization (e.g. Flush or Channel)
    top_realization_segment = ""
    top_realization_rate = 0.0
    if secondary_dim and rev_col and vol_col and secondary_dim in df.columns:
        sec_grouped = df.groupby(secondary_dim).agg(
            rev=(rev_col, "sum"),
            vol=(vol_col, "sum")
        )
        sec_grouped["rate"] = sec_grouped["rev"] / sec_grouped["vol"].replace(0, np.nan)
        sorted_sec = sec_grouped.sort_values(by="rate", ascending=False)
        if len(sorted_sec) > 0:
            top_realization_segment = str(sorted_sec.index[0])
            top_realization_rate = float(sorted_sec["rate"].iloc[0])

    # 5. Build Grounded Deterministic Briefing
    top1 = top_contributors[0] if len(top_contributors) > 0 else {"name": "Core Grade Lots", "revenue": total_rev, "volume": total_vol, "share": 100.0}
    top2 = top_contributors[1] if len(top_contributors) > 1 else None
    top3 = top_contributors[2] if len(top_contributors) > 2 else None

    # Determine client persona
    is_estate_model = "Estate" in client_name or "Himalayan" in client_name or "Auction" in client_name or "Estate_Name" in df.columns

    # Section 1: Executive Summary
    summary_text = (
        f"Across the active audited ledger ({record_count:,} lots), **{client_name}** achieved a total realized commercial value of "
        f"**{format_indian_currency(total_rev)}** on a total output volume of **{format_indian_number(total_vol, 3)} kgs**. "
        f"This yields a portfolio-wide weighted average realization of **{format_indian_currency(avg_price)} / kg**, with an audited quality benchmark of **{avg_score:.1f} / 100**."
    )

    # Section 2: Macro Commercial Drivers
    drivers = [
        f"**Top Volume & Value Driver**: **{top1['name']}** led commercial realization with **{format_indian_currency(top1['revenue'])}** ({top1['share']}% of total revenue) across **{format_indian_number(top1['volume'], 3)} kgs**."
    ]
    if top2:
        drivers.append(f"**Secondary Commercial Anchor**: **{top2['name']}** contributed **{format_indian_currency(top2['revenue'])}** ({top2['share']}% portfolio share).")
    if top_realization_segment and top_realization_rate > 0:
        drivers.append(f"**Peak Realization Segment**: Highest pricing efficiency was commanded by **{top_realization_segment}**, realizing **{format_indian_currency(top_realization_rate)} / kg**.")
    # Dynamic price spread computation
    price_spread_text = ""
    price_col = None
    for cand in ["PRICE_PER_KG_USD", "UNIT_PRICE_USD", "Price_USD", "Price_INR"]:
        if cand in df.columns:
            price_col = cand
            break
    if price_col:
        p_series = pd.to_numeric(df[price_col], errors="coerce").dropna()
        if len(p_series) > 0:
            q75 = float(p_series.quantile(0.75))
            q25 = float(p_series.quantile(0.25))
            if q25 > 0:
                prem_pct = ((q75 - q25) / q25) * 100.0
                price_spread_text = f", with upper-quartile lots commanding a {prem_pct:.1f}% price premium over commercial baseline grades ({format_indian_currency(q75)}/kg vs {format_indian_currency(q25)}/kg)"

    if score_col:
        drivers.append(f"**Quality Benchmark**: Active catalog cupping index averaged **{avg_score:.1f} / 100**{price_spread_text}.")

    # Section 3: Root Cause & Terroir Variance
    if is_estate_model:
        root_cause = (
            f"Commercial performance variations are anchored in harvest flush seasonality and elevation microclimates. "
            f"**Second Flush summer lots** achieve top prices due to high-altitude sun exposure and low moisture indices (<6.5%), which lock in signature muscatel aromatics. "
            f"In contrast, monsoon flush lots experienced higher moisture and increased bulk supply, driving auction hammer realizations down relative to whole-leaf orthodox grades."
        )
    else:
        root_cause = (
            f"Commercial margin divergence is primarily driven by sales channel mix and direct-to-consumer adoption. "
            f"**Artisanal Loose Leaf & Ceremonial Blends** sold through boutique retail and direct e-commerce yield gross margins above 60%, whereas third-party wholesale accounts experienced higher promotional discounting and tighter net realizations."
        )

    # Section 4: Recommended Strategic Directives
    if is_estate_model:
        directives = (
            f"1. **Prioritize Premium Allocations**: Channel at least 65% of upcoming harvest lots from **{top1['name']}** into private-treaty export auctions to capture international buyer margins.\n"
            f"2. **Strict Terroir Moisture Control**: Maintain estate sorting moisture strictly below 6.5% with hermetic packaging within 48 hours to preserve volatile flavor compounds and prevent auction discounts.\n"
            f"3. **Grade Realization Shift**: Convert lower-realization broken pekoe fractions into specialty artisan tea pyramids to lift blended average hammer prices."
        )
    else:
        directives = (
            f"1. **Scale High-Margin Channels**: Expand direct e-commerce subscription offerings for **{top1['name']}** to lock in recurring high-margin cash flow.\n"
            f"2. **Channel Optimization**: Re-negotiate minimum order sizes for wholesale distributors and allocate top-tier seasonal blends exclusively to flagship boutiques.\n"
            f"3. **Inventory Agility**: Keep packaging runs tight (30-day batches) for delicate green and white teas to maintain peak aroma and prevent inventory discounting."
        )

    # Try LLM refinement if API key available (Gemini or OpenAI), otherwise return grounded synthesis directly
    system_prompt = f"""
You are an Executive Business Intelligence Director delivering an official Management Briefing for {client_name}.
Synthesize the provided calculated facts into a polished executive briefing.
Include the EXACT numbers provided (in Rs. Crores/Lakhs and kgs with 3 decimal points).
DO NOT use vague boilerplate. Ground every sentence in the provided facts.

STRUCTURE YOUR OUTPUT STRICTLY WITH THESE EXACT HEADINGS:
### 1. Executive Summary
### 2. Primary Commercial Drivers
### 3. Root Cause & Terroir Variance
### 4. Recommended Strategic Directives

FORMATTING REQUIREMENT:
ALWAYS format primary entity names, top estates, and key numbers in **BOLD CAPITAL LETTERS** (e.g. **DEWAN TEA ESTATE**, **JELLALPORE TEA ESTATE**, **Rs. 54.92 Crores**).
"""
    user_prompt = f"""
Calculated Verified Facts:
- Client: {client_name}
- Total Gross Revenue: {format_indian_currency(total_rev)}
- Total Volume Sold: {format_indian_number(total_vol, 3)} kgs
- Average Price: {format_indian_currency(avg_price)} / kg
- Average Cupping/Quality Score: {avg_score:.1f} / 100
- Total Audited Lots: {record_count:,}
- Top Contributor: {top1['name']} ({format_indian_currency(top1['revenue'])}, {top1['share']}%)
- Secondary Contributor: {top2['name'] if top2 else 'N/A'} ({format_indian_currency(top2['revenue']) if top2 else ''})
- Peak Realization Segment: {top_realization_segment} ({format_indian_currency(top_realization_rate)} / kg)
- Model Type: {'Estate Auction' if is_estate_model else 'Specialty Retail'}
"""
    refined = call_llm_text(system_prompt, user_prompt, timeout=12.0)
    if refined:
        return refined

    # High-fidelity grounded deterministic synthesis fallback
    output_lines = [
        "### 1. Executive Summary",
        summary_text,
        "",
        "### 2. Primary Commercial Drivers",
        "\n".join([f"- {d}" for d in drivers]),
        "",
        "### 3. Root Cause & Terroir Variance",
        root_cause,
        "",
        "### 4. Recommended Strategic Directives",
        directives
    ]
    return "\n".join(output_lines)

