import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "data"

# ==============================================================================
# 1. CLIENT ALPHA: RELATIONAL TEA ESTATE AUCTION SCHEMA
# ==============================================================================
alpha_dir = BASE_DIR / "client_alpha"
df_alpha = pd.read_csv(alpha_dir / "himalayan_estate_teas.csv")

# 1A. Dim Estates
estates = df_alpha[["ESTATE", "REGION"]].drop_duplicates().reset_index(drop=True)
estates["ESTATE_ID"] = [f"EST-{i+1:03d}" for i in range(len(estates))]

# Add enterprise terroir metadata
elevation_map = {
    "Darjeeling": 1950,
    "Nilgiri": 1800,
    "Upper Assam": 120,
    "Dooars": 180,
    "Terai": 130
}
estates["ELEVATION_METERS"] = estates["REGION"].map(elevation_map).fillna(500)
estates["ORGANIC_CERTIFIED"] = estates["REGION"].apply(lambda r: "Yes" if r in ["Darjeeling", "Nilgiri"] else "No")
dim_estates = estates[["ESTATE_ID", "ESTATE", "REGION", "ELEVATION_METERS", "ORGANIC_CERTIFIED"]]
dim_estates.to_csv(alpha_dir / "dim_estates.csv", index=False)

# 1B. Dim Grades
grades = df_alpha[["TEA_GRADE"]].drop_duplicates().reset_index(drop=True)
grades["GRADE_ID"] = [f"GRD-{i+1:03d}" for i in range(len(grades))]
grades["LEAF_TYPE"] = grades["TEA_GRADE"].apply(lambda g: "Whole Leaf" if "Orthodox" in g or "FOP" in g else "Broken / BOP" if "BOP" in g else "Fannings / Dust")
grades["PROCESSING_METHOD"] = grades["TEA_GRADE"].apply(lambda g: "CTC" if "CTC" in g else "Orthodox")
dim_grades = grades[["GRADE_ID", "TEA_GRADE", "LEAF_TYPE", "PROCESSING_METHOD"]]
dim_grades.to_csv(alpha_dir / "dim_grades.csv", index=False)

# 1C. Dim Buyers
buyers = df_alpha[["BUYER_COUNTRY"]].drop_duplicates().reset_index(drop=True)
buyers["BUYER_ID"] = [f"BUY-{i+1:03d}" for i in range(len(buyers))]
buyer_name_map = {
    "Germany": "Haelssen & Lyon Global",
    "Japan": "Lupicia Artisan Importers",
    "United Kingdom": "Twinings & Fortnum Procurement",
    "United States": "Harney & Sons Specialty",
    "UAE": "Al-Futtaim Tea Merchants",
    "France": "Mariage Frères Trading",
    "India": "Tata Consumer Products Domestic",
    "Australia": "T2 Tea Melbourne",
    "Canada": "DAVIDsTEA Sourcing"
}
buyers["BUYER_NAME"] = buyers["BUYER_COUNTRY"].map(buyer_name_map).fillna("Global Enterprise Importers")
buyers["BUYER_TIER"] = ["Tier 1 Global Partner" if i % 2 == 0 else "Artisan Importer" for i in range(len(buyers))]
dim_buyers = buyers[["BUYER_ID", "BUYER_NAME", "BUYER_COUNTRY", "BUYER_TIER"]]
dim_buyers.to_csv(alpha_dir / "dim_buyers.csv", index=False)

# 1D. Fact Auction Lots (Fact Table linking Foreign Keys)
fact_alpha = df_alpha.copy()
fact_alpha = fact_alpha.merge(dim_estates[["ESTATE", "ESTATE_ID"]], on="ESTATE", how="left")
fact_alpha = fact_alpha.merge(dim_grades[["TEA_GRADE", "GRADE_ID"]], on="TEA_GRADE", how="left")
fact_alpha = fact_alpha.merge(dim_buyers[["BUYER_COUNTRY", "BUYER_ID"]], on="BUYER_COUNTRY", how="left")

fact_lots = fact_alpha[[
    "LOT_ID", "SALE_DATE", "ESTATE_ID", "GRADE_ID", "BUYER_ID",
    "SEASON_FLUSH", "AUCTION_CENTER", "VOLUME_KG",
    "PRICE_PER_KG_USD", "TOTAL_REVENUE_USD", "QUALITY_SCORE", "MOISTURE_PCT"
]]
fact_lots.to_csv(alpha_dir / "fact_auction_lots.csv", index=False)

# 1E. Fact Shipments (Bridge table)
shipments_alpha = df_alpha[["LOT_ID", "SHIPMENT_STATUS", "DAYS_IN_TRANSIT"]].copy()
shipments_alpha["SHIPMENT_ID"] = [f"SHP-A-{i+1:05d}" for i in range(len(shipments_alpha))]
carrier_map = ["Maersk Line", "DHL Global Forwarding", "MSC Mediterranean Shipping", "Blue Dart Express", "Hapag-Lloyd"]
shipments_alpha["LOGISTICS_CARRIER"] = [carrier_map[i % len(carrier_map)] for i in range(len(shipments_alpha))]
fact_shipments_alpha = shipments_alpha[["SHIPMENT_ID", "LOT_ID", "SHIPMENT_STATUS", "DAYS_IN_TRANSIT", "LOGISTICS_CARRIER"]]
fact_shipments_alpha.to_csv(alpha_dir / "fact_shipments.csv", index=False)

# 1F. Schema Relationships Metadata
alpha_schema = {
    "client_id": "client_alpha",
    "schema_type": "Star Schema (Relational Data Model)",
    "primary_fact_table": "fact_auction_lots",
    "tables": {
        "fact_auction_lots": {
            "type": "FACT",
            "file": "fact_auction_lots.csv",
            "primary_key": "LOT_ID",
            "foreign_keys": {
                "ESTATE_ID": {"references": "dim_estates.ESTATE_ID", "relationship": "MANY_TO_ONE"},
                "GRADE_ID": {"references": "dim_grades.GRADE_ID", "relationship": "MANY_TO_ONE"},
                "BUYER_ID": {"references": "dim_buyers.BUYER_ID", "relationship": "MANY_TO_ONE"}
            }
        },
        "dim_estates": {
            "type": "DIMENSION",
            "file": "dim_estates.csv",
            "primary_key": "ESTATE_ID",
            "attributes": ["ESTATE", "REGION", "ELEVATION_METERS", "ORGANIC_CERTIFIED"]
        },
        "dim_grades": {
            "type": "DIMENSION",
            "file": "dim_grades.csv",
            "primary_key": "GRADE_ID",
            "attributes": ["TEA_GRADE", "LEAF_TYPE", "PROCESSING_METHOD"]
        },
        "dim_buyers": {
            "type": "DIMENSION",
            "file": "dim_buyers.csv",
            "primary_key": "BUYER_ID",
            "attributes": ["BUYER_NAME", "BUYER_COUNTRY", "BUYER_TIER"]
        },
        "fact_shipments": {
            "type": "BRIDGE_FACT",
            "file": "fact_shipments.csv",
            "primary_key": "SHIPMENT_ID",
            "foreign_keys": {
                "LOT_ID": {"references": "fact_auction_lots.LOT_ID", "relationship": "ONE_TO_ONE"}
            },
            "attributes": ["SHIPMENT_STATUS", "DAYS_IN_TRANSIT", "LOGISTICS_CARRIER"]
        }
    }
}

with open(alpha_dir / "schema_relationships.json", "w") as f:
    json.dump(alpha_schema, f, indent=2)

print("[OK] Created relational tables and schema for client_alpha:")
print(f"  - dim_estates.csv: {len(dim_estates)} rows")
print(f"  - dim_grades.csv: {len(dim_grades)} rows")
print(f"  - dim_buyers.csv: {len(dim_buyers)} rows")
print(f"  - fact_auction_lots.csv: {len(fact_lots)} rows")
print(f"  - fact_shipments.csv: {len(fact_shipments_alpha)} rows")


# ==============================================================================
# 2. CLIENT BETA: RELATIONAL SPECIALTY RETAIL SCHEMA
# ==============================================================================
beta_dir = BASE_DIR / "client_beta"
df_beta = pd.read_csv(beta_dir / "zenith_specialty_retail.csv")

# 2A. Dim Products
products = df_beta[["PRODUCT_NAME", "CATEGORY", "PACKAGING"]].drop_duplicates().reset_index(drop=True)
products["PRODUCT_ID"] = [f"PRD-{i+1:03d}" for i in range(len(products))]
dim_products = products[["PRODUCT_ID", "PRODUCT_NAME", "CATEGORY", "PACKAGING"]]
dim_products.to_csv(beta_dir / "dim_products.csv", index=False)

# 2B. Dim Channels
channels = df_beta[["SALES_CHANNEL"]].drop_duplicates().reset_index(drop=True)
channels["CHANNEL_ID"] = [f"CHN-{i+1:03d}" for i in range(len(channels))]
channel_type_map = {
    "Direct-to-Consumer Website": "Digital E-Commerce",
    "Gourmet Grocery & Boutiques": "Physical Retail",
    "Corporate Subscriptions": "B2B Recurring",
    "HoReCa Fine Dining": "Hospitality"
}
channels["CHANNEL_TYPE"] = channels["SALES_CHANNEL"].map(channel_type_map).fillna("Omnichannel")
dim_channels = channels[["CHANNEL_ID", "SALES_CHANNEL", "CHANNEL_TYPE"]]
dim_channels.to_csv(beta_dir / "dim_channels.csv", index=False)

# 2C. Dim Regions / Markets
regions = df_beta[["MARKET_REGION"]].drop_duplicates().reset_index(drop=True)
regions["REGION_ID"] = [f"MKT-{i+1:03d}" for i in range(len(regions))]
currency_map = {
    "North America": "USD",
    "Western Europe": "EUR",
    "East Asia": "JPY",
    "Middle East": "AED",
    "India Domestic": "INR"
}
regions["LOCAL_CURRENCY"] = regions["MARKET_REGION"].map(currency_map).fillna("USD")
dim_regions = regions[["REGION_ID", "MARKET_REGION", "LOCAL_CURRENCY"]]
dim_regions.to_csv(beta_dir / "dim_regions.csv", index=False)

# 2D. Fact Sales Orders
fact_beta = df_beta.copy()
fact_beta = fact_beta.merge(dim_products[["PRODUCT_NAME", "CATEGORY", "PACKAGING", "PRODUCT_ID"]], on=["PRODUCT_NAME", "CATEGORY", "PACKAGING"], how="left")
fact_beta = fact_beta.merge(dim_channels[["SALES_CHANNEL", "CHANNEL_ID"]], on="SALES_CHANNEL", how="left")
fact_beta = fact_beta.merge(dim_regions[["MARKET_REGION", "REGION_ID"]], on="MARKET_REGION", how="left")

fact_orders = fact_beta[[
    "ORDER_ID", "ORDER_DATE", "PRODUCT_ID", "CHANNEL_ID", "REGION_ID",
    "UNITS_SOLD", "UNIT_PRICE_USD", "DISCOUNT_PCT", "NET_SALES_USD",
    "GROSS_MARGIN_PCT", "CUSTOMER_RATING", "FULFILLMENT_DAYS"
]]
fact_orders.to_csv(beta_dir / "fact_sales_orders.csv", index=False)

# 2E. Schema Relationships Metadata
beta_schema = {
    "client_id": "client_beta",
    "schema_type": "Star Schema (Relational Data Model)",
    "primary_fact_table": "fact_sales_orders",
    "tables": {
        "fact_sales_orders": {
            "type": "FACT",
            "file": "fact_sales_orders.csv",
            "primary_key": "ORDER_ID",
            "foreign_keys": {
                "PRODUCT_ID": {"references": "dim_products.PRODUCT_ID", "relationship": "MANY_TO_ONE"},
                "CHANNEL_ID": {"references": "dim_channels.CHANNEL_ID", "relationship": "MANY_TO_ONE"},
                "REGION_ID": {"references": "dim_regions.REGION_ID", "relationship": "MANY_TO_ONE"}
            }
        },
        "dim_products": {
            "type": "DIMENSION",
            "file": "dim_products.csv",
            "primary_key": "PRODUCT_ID",
            "attributes": ["PRODUCT_NAME", "CATEGORY", "PACKAGING"]
        },
        "dim_channels": {
            "type": "DIMENSION",
            "file": "dim_channels.csv",
            "primary_key": "CHANNEL_ID",
            "attributes": ["SALES_CHANNEL", "CHANNEL_TYPE"]
        },
        "dim_regions": {
            "type": "DIMENSION",
            "file": "dim_regions.csv",
            "primary_key": "REGION_ID",
            "attributes": ["MARKET_REGION", "LOCAL_CURRENCY"]
        }
    }
}

with open(beta_dir / "schema_relationships.json", "w") as f:
    json.dump(beta_schema, f, indent=2)

print("\n[OK] Created relational tables and schema for client_beta:")
print(f"  - dim_products.csv: {len(dim_products)} rows")
print(f"  - dim_channels.csv: {len(dim_channels)} rows")
print(f"  - dim_regions.csv: {len(dim_regions)} rows")
print(f"  - fact_sales_orders.csv: {len(fact_orders)} rows")
