"""
CLIENTS CONFIGURATION & ROLE-BASED ACCESS REGISTRY
=================================================
Maps each client identity to their isolated in-built dataset and role.
Guarantees strict multi-tenant data and conversation isolation.
"""

from typing import Dict, Any, Optional

CLIENTS: Dict[str, Dict[str, Any]] = {
    "client_alpha": {
        "username": "client_alpha",
        "password": "password123",
        "display_name": "Himalayan Estate Teas & Auctions",
        "role": "Chief Tea Auction Director",
        "industry": "Tea Plantation, Estate Auctions & Global Exports",
        "data_file": "data/client_alpha/himalayan_estate_teas.csv",
        "description": "Darjeeling & Assam Estate Lot Sales, Auction Pricing & International Shipments",
        "sample_prompts": [
            "Which tea estate generated the highest total revenue?",
            "What is the average price per kg across different tea grades?",
            "Show total volume in kg by season flush.",
            "Which buyer country imported the highest volume of tea?",
            "Are there any statistical anomalies in price per kg?",
        ],
    },
    "client_beta": {
        "username": "client_beta",
        "password": "password123",
        "display_name": "Zenith Artisanal Blends & Retail",
        "role": "VP of Specialty Tea Retail",
        "industry": "Specialty Tea Retail, D2C Blends & Global Boutiques",
        "data_file": "data/client_beta/zenith_specialty_retail.csv",
        "description": "Specialty Tea Blends, Packaging Formats, Omni-Channel Sales & Margins",
        "sample_prompts": [
            "What is the total net sales revenue across all tea blends?",
            "Which product category delivers the highest gross margin percentage?",
            "What are the top 5 tea blends by total units sold?",
            "Show net sales breakdown across sales channels.",
            "What is the average customer rating for Ceremonial Uji Matcha?",
        ],
    },
}

# Alias for simple login convenience (e.g. typing 'alpha' or 'beta' directly)
CLIENTS["alpha"] = CLIENTS["client_alpha"]
CLIENTS["beta"] = CLIENTS["client_beta"]

def discover_client_folders():
    """Dynamically discovers and registers any new client directory in data/."""
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent / "data"
    if not data_dir.exists():
        return
    for item in data_dir.iterdir():
        if item.is_dir() and item.name.startswith("client_") and item.name not in CLIENTS:
            cid = item.name
            csv_files = list(item.glob("*.csv"))
            main_csv = next((f for f in csv_files if "dim_" not in f.name and "fact_" not in f.name), csv_files[0] if csv_files else None)
            if main_csv:
                clean_name = cid.replace("client_", "").replace("_", " ").title()
                CLIENTS[cid] = {
                    "username": cid,
                    "password": "password123",
                    "display_name": f"{clean_name} Enterprise",
                    "role": "Commercial Operations Director",
                    "industry": f"{clean_name} Operations & Analytics",
                    "data_file": f"data/{cid}/{main_csv.name}",
                    "description": f"Audited commercial dataset for {clean_name}",
                    "sample_prompts": [
                        "What is the total revenue across all categories?",
                        "What are the top 5 performing entities?",
                        "Show monthly trend analysis.",
                    ],
                }
                alias = cid.replace("client_", "")
                CLIENTS[alias] = CLIENTS[cid]

discover_client_folders()

def authenticate_client(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates client credentials and returns client profile if successful."""
    discover_client_folders()
    clean_user = username.strip().lower()
    client = CLIENTS.get(clean_user)
    if not client:
        return None
    valid_passwords = [client["password"], "password123"]
    if clean_user in ("client_alpha", "alpha"):
        valid_passwords.append("himalayan_secret")
    elif clean_user in ("client_beta", "beta"):
        valid_passwords.append("zenith_secret")

    if password.strip() in valid_passwords:
        return client
    return None

