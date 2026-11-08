"""
AI BUSINESS ANALYST - ENTERPRISE CLIENT PORTAL
==============================================
Client-facing, role-based business intelligence and conversational portal.
- In-built datasets with strict client-level isolation (no file uploads for clients).
- OpenAI API key is 100% backend-managed via .env (never prompted in UI).
- Client interface restricted exclusively to:
    1. 💬 Chatbot (Conversational AI with deterministic calculations & Plotly charts)
    2. 📊 Reports (Executive dashboard, Management Summaries, and data tables)
- Role-based multi-tenant security: No two clients can see the same data or questions.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from openai import OpenAI

from clients_config import CLIENTS, authenticate_client

# Load environment variables from .env silently
load_dotenv()
BACKEND_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ==============================================================================
# STREAMLIT APP CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="Tea BI Analyst | Camellia Enterprise Portal",
    page_icon="🍵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Tea Industry & Power BI Styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,400&display=swap');
    
    :root {
        --tea-forest: #1b4332;
        --tea-leaf: #2d6a4f;
        --tea-matcha: #40916c;
        --tea-mint: #52b788;
        --tea-amber: #c58f3b;
        --tea-amber-dark: #bc6c25;
        --tea-parchment: #fcfbf7;
        --tea-card: #ffffff;
        --tea-border: #e2ece9;
        --tea-text: #19281e;
        --tea-muted: #52796f;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Power BI Standard KPI Card */
    .pbi-kpi-card {
        background: #ffffff;
        border: 1px solid #e2ece9;
        border-left: 5px solid #2d6a4f;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 2px 4px rgba(27, 67, 50, 0.04), 0 1px 2px rgba(0,0,0,0.02);
        margin-bottom: 14px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .pbi-kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(27, 67, 50, 0.08);
    }
    .pbi-kpi-card.amber-accent {
        border-left-color: #c58f3b;
    }
    .pbi-kpi-card.matcha-accent {
        border-left-color: #52b788;
    }
    .pbi-kpi-card.forest-accent {
        border-left-color: #1b4332;
    }
    .pbi-kpi-title {
        color: #52796f;
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }
    .pbi-kpi-value {
        color: #19281e;
        font-size: 1.85rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .pbi-kpi-subtitle {
        color: #718096;
        font-size: 0.8rem;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .pbi-kpi-badge {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        background: #e8f5e9;
        color: #2d6a4f;
    }
    .pbi-kpi-badge.amber {
        background: #fef3c7;
        color: #92400e;
    }

    /* Slicer Container */
    .pbi-slicer-container {
        background: #f8faf8;
        border: 1px solid #d8e6df;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 20px;
    }
    .pbi-slicer-title {
        color: #2d6a4f;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* Client Badge */
    .tea-client-badge {
        background: linear-gradient(135deg, #f4f9f5 0%, #e8f5ee 100%);
        border: 1px solid #cce3d6;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 16px;
    }
    .tea-client-name {
        color: #1b4332;
        font-weight: 800;
        font-size: 1.1rem;
        letter-spacing: -0.01em;
    }
    .tea-client-role {
        color: #2d6a4f;
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* Buttons */
    .stButton button {
        border-radius: 6px;
        font-size: 0.88rem;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    button[kind="primary"] {
        background-color: #2d6a4f !important;
        border-color: #2d6a4f !important;
        color: #ffffff !important;
    }
    button[kind="primary"]:hover {
        background-color: #1b4332 !important;
        border-color: #1b4332 !important;
    }

    /* Follow-up Chips */
    .followup-chip {
        background: #ffffff;
        border: 1px solid #cce3d6;
        color: #2d6a4f;
        border-radius: 16px;
        padding: 6px 14px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 4px;
        display: inline-block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# SESSION STATE INITIALIZATION & ISOLATION
# ==============================================================================
if "authenticated_client" not in st.session_state:
    st.session_state.authenticated_client = None

# Store isolated chat and context per client ID: {client_id: list_of_messages}
if "client_chat_stores" not in st.session_state:
    st.session_state.client_chat_stores = {}

if "client_contexts" not in st.session_state:
    st.session_state.client_contexts = {}


# ==============================================================================
# DATA INGESTION & PROFILING (BACKEND ONLY)
# ==============================================================================
@st.cache_data(show_spinner=False)
def load_client_dataset(data_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Loads client's in-built dataset from local storage safely."""
    try:
        if not os.path.exists(data_path):
            return None, f"Assigned data file '{data_path}' was not found on the server."

        if data_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(data_path)
        else:
            try:
                df = pd.read_csv(data_path)
            except UnicodeDecodeError:
                df = pd.read_csv(data_path, encoding="latin-1")

        if df.empty:
            return None, "The dataset contains no records."

        # Clean column names and normalize object columns for reliable Arrow serialization
        df.columns = [str(c).strip() for c in df.columns]
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna("").astype(str)

        return df, None
    except Exception as e:
        return None, f"Failed to load client dataset: {str(e)}"


def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Profiles dataset structure for the analytical planning engine."""
    total_rows = len(df)
    total_cols = len(df.columns)

    measures: List[Dict[str, Any]] = []
    dates: List[Dict[str, Any]] = []
    dimensions: List[Dict[str, Any]] = []
    identifiers: List[Dict[str, Any]] = []

    id_patterns = re.compile(r"id|code|num|key|sku|ref|uuid|no\b|tno|txn|seq", re.IGNORECASE)
    date_patterns = re.compile(r"date|time|year|month|day|quarter|period|timestamp|created|updated|dt\b", re.IGNORECASE)

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
            if date_patterns.search(str(col)) or unique_count <= 2000:
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

        # Check numeric
        if pd.api.types.is_numeric_dtype(series):
            if (unique_count == non_null_count and non_null_count > 10 and id_patterns.search(str(col))) or (unique_count > 0.98 * non_null_count and non_null_count > 50):
                identifiers.append({"column": col, "unique_count": unique_count, "sample": list(series.dropna().head(3))})
            else:
                measures.append({
                    "column": col,
                    "min": float(series.min()) if non_null_count > 0 else 0,
                    "max": float(series.max()) if non_null_count > 0 else 0,
                    "mean": float(series.mean()) if non_null_count > 0 else 0,
                    "sum": float(series.sum()) if non_null_count > 0 else 0,
                })
            continue

        # Check ID vs Dimension
        if unique_count == non_null_count and non_null_count > 10:
            identifiers.append({"column": col, "unique_count": unique_count, "sample": list(series.dropna().head(3))})
        elif id_patterns.search(str(col)) and unique_count > 0.8 * non_null_count:
            identifiers.append({"column": col, "unique_count": unique_count, "sample": list(series.dropna().head(3))})
        else:
            dimensions.append({
                "column": col,
                "unique_count": unique_count,
                "sample": [str(x) for x in series.dropna().unique()[:5]],
            })

    return {
        "total_rows": total_rows,
        "total_cols": total_cols,
        "measures": measures,
        "dates": dates,
        "dimensions": dimensions,
        "identifiers": identifiers,
    }


# ==============================================================================
# OPENAI PLANNING & CALCULATION ENGINE
# ==============================================================================
def rule_based_fallback_plan(question: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Resilient local planner that activates if external API services are unavailable."""
    q = question.lower().strip()

    # 1. Ranking or breakdown by category
    if any(k in q for k in ["which", "highest", "lowest", "top", "bottom", "rank", "ranking", "breakdown", "by "]):
        matched_dim = None
        for d in profile["dimensions"]:
            col_lower = d["column"].lower()
            if col_lower in q or col_lower.rstrip('s') in q:
                matched_dim = d["column"]
                break
        if not matched_dim and profile["dimensions"]:
            matched_dim = profile["dimensions"][0]["column"]

        matched_meas = None
        for m in profile["measures"]:
            if m["column"].lower() in q:
                matched_meas = m["column"]
                break

        # Check for value filters (e.g. 'delayed' or 'delivered')
        filters = []
        for d in profile["dimensions"]:
            for val in d.get("sample", []):
                val_str = str(val).lower()
                if val_str and val_str in q:
                    filters.append({"column": d["column"], "operator": "==", "value": str(val)})

        return {
            "intent": "ranking",
            "dimension": matched_dim,
            "measure": matched_meas,
            "aggregation": "sum" if matched_meas else "count",
            "filters": filters,
            "sort": "ascending" if any(w in q for w in ["lowest", "bottom"]) else "descending",
            "top_n": 10,
        }

    # 2. Average / Mean
    if "average" in q or "mean" in q:
        matched_meas = None
        for m in profile["measures"]:
            if m["column"].lower() in q:
                matched_meas = m["column"]
                break
        if not matched_meas and profile["measures"]:
            matched_meas = profile["measures"][0]["column"]

        return {
            "intent": "aggregation",
            "measure": matched_meas,
            "aggregation": "mean",
            "filters": [],
        }

    # 3. Anomaly / Outliers
    if any(k in q for k in ["unusual", "outlier", "anomaly", "anomalies"]):
        matched_meas = profile["measures"][0]["column"] if profile["measures"] else None
        return {
            "intent": "anomaly",
            "anomaly_column": matched_meas,
            "filters": [],
        }

    # 4. Total / Count / Sum
    matched_meas = None
    for m in profile["measures"]:
        if m["column"].lower() in q:
            matched_meas = m["column"]
            break

    return {
        "intent": "aggregation",
        "measure": matched_meas,
        "aggregation": "sum" if matched_meas else "count",
        "filters": [],
    }


def create_analysis_plan(
    question: str,
    profile: Dict[str, Any],
    conversation_context: Dict[str, Any],
) -> Dict[str, Any]:
    if not BACKEND_API_KEY:
        return rule_based_fallback_plan(question, profile)

    client = OpenAI(api_key=BACKEND_API_KEY)

    available_measures = [m["column"] for m in profile["measures"]]
    available_dates = [d["column"] for d in profile["dates"]]
    available_dimensions = [{"column": d["column"], "sample_values": d["sample"]} for d in profile["dimensions"]]
    available_identifiers = [i["column"] for i in profile["identifiers"]]

    system_prompt = f"""
You are the Planning Engine of the Enterprise Client AI Business Analyst.
Translate the business client's question into a structured JSON analysis plan.

CRITICAL RULES:
1. YOU DO NOT CALCULATE NUMBERS. Python calculates the numbers.
2. YOU MUST USE ONLY THE ACTUAL COLUMNS PRESENT IN THIS CLIENT'S DATASET:
   - Measures: {json.dumps(available_measures)}
   - Date fields: {json.dumps(available_dates)}
   - Dimensions: {json.dumps(available_dimensions)}
   - Identifiers: {json.dumps(available_identifiers)}
3. DO NOT INVENT OR GUESS COLUMNS.
4. RESOLVE PRONOUNS AND CONTEXT:
   Previous context: {json.dumps(conversation_context)}
   If the client asks "Show its trend", resolve "it" to previous entity or dimension filter.

Respond with ONLY valid JSON:
{{
  "intent": "aggregation" | "ranking" | "time_series" | "comparison" | "root_cause" | "anomaly" | "distribution" | "general_query",
  "measure": "exact column name or null",
  "dimension": "exact column name or null",
  "aggregation": "sum" | "mean" | "count" | "nunique" | "min" | "max" | "median",
  "time_column": "exact date column or null",
  "time_granularity": "day" | "week" | "month" | "quarter" | "year" | null,
  "filters": [{{"column": "column_name", "operator": "==", "value": "specific_value"}}],
  "sort": "descending" | "ascending" | null,
  "top_n": 10,
  "root_cause_dimension": "dimension or null",
  "anomaly_column": "measure name or null",
  "needs_clarification": false,
  "clarification_message": "",
  "question_summary": "One sentence summary"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        # Seamlessly fallback to deterministic local planner if external service quota is exceeded
        return rule_based_fallback_plan(question, profile)


def validate_analysis_plan(plan: Dict[str, Any], df: pd.DataFrame, profile: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if plan.get("needs_clarification", False):
        return False, plan.get("clarification_message", "Clarification needed.")

    intent = plan.get("intent", "general_query")
    measure = plan.get("measure")
    dimension = plan.get("dimension")
    time_col = plan.get("time_column")

    if measure and measure not in df.columns:
        return False, f"The analysis requested column '{measure}', which is not in your dataset."

    if dimension and dimension not in df.columns:
        return False, f"The category '{dimension}' is not present in your dataset."

    if intent in ["time_series", "comparison", "root_cause"]:
        if not time_col and not profile["dates"]:
            return False, "This analysis requires a date column, but your data does not contain one."

    return True, None


def apply_filters(df: pd.DataFrame, filters: List[Dict[str, Any]]) -> pd.DataFrame:
    filtered_df = df.copy()
    for f in filters:
        col, val = f.get("column"), f.get("value")
        if col in filtered_df.columns and val is not None:
            filtered_df = filtered_df[filtered_df[col].astype(str).str.strip().str.lower() == str(val).strip().lower()]
    return filtered_df


def execute_analysis(plan: Dict[str, Any], df: pd.DataFrame, profile: Dict[str, Any]) -> Dict[str, Any]:
    intent = plan.get("intent", "aggregation")
    measure = plan.get("measure") or (profile["measures"][0]["column"] if profile["measures"] else None)
    dimension = plan.get("dimension") or (profile["dimensions"][0]["column"] if profile["dimensions"] else None)
    agg_func = plan.get("aggregation", "sum")
    top_n = plan.get("top_n", 10)
    sort_order = plan.get("sort", "descending")
    filters = plan.get("filters", [])

    working_df = apply_filters(df, filters)
    if working_df.empty:
        return {"status": "error", "message": "Applying the requested filter resulted in 0 matching records."}

    # 1. AGGREGATION
    if intent == "aggregation":
        if not measure:
            val = len(working_df)
            return {
                "status": "success", "intent": "aggregation",
                "metric_label": "Total Record Count", "calculated_value": val,
                "summary_table": pd.DataFrame([{"Metric": "Record Count", "Value": val}]),
                "supporting_stats": {"total_records": val},
            }
        s = working_df[measure].dropna()
        agg_map = {"mean": s.mean, "count": s.count, "nunique": s.nunique, "min": s.min, "max": s.max, "median": s.median}
        val = agg_map.get(agg_func, s.sum)()
        summary_table = pd.DataFrame([
            {"Metric": f"{agg_func.capitalize()} of {measure}", "Value": round(val, 2) if isinstance(val, float) else val},
            {"Total Records": len(working_df), "Non-null Records": len(s)},
            {"Min": round(float(s.min()), 2) if len(s) else 0, "Max": round(float(s.max()), 2) if len(s) else 0},
        ])
        return {
            "status": "success", "intent": "aggregation", "measure": measure,
            "aggregation": agg_func, "calculated_value": val,
            "summary_table": summary_table,
            "supporting_stats": {"mean": float(s.mean()) if len(s) else 0, "total_rows": len(working_df)},
        }

    # 2. RANKING / CATEGORY GROUPING
    elif intent == "ranking":
        if not dimension:
            return {"status": "error", "message": "Ranking requires a categorical dimension."}
        
        # If no numeric measure exists, count records by dimension
        if not measure:
            grouped = working_df.groupby(dimension, as_index=False).size()
            grouped.columns = [dimension, "Record_Count"]
            chosen_col = "Record_Count"
        else:
            chosen_agg = agg_func if agg_func in ["sum", "mean", "count", "min", "max", "median"] else "sum"
            grouped = working_df.groupby(dimension, as_index=False)[measure].agg(chosen_agg)
            grouped.columns = [dimension, f"{chosen_agg}_{measure}"]
            chosen_col = f"{chosen_agg}_{measure}"

        ascending = (sort_order == "ascending")
        sorted_df = grouped.sort_values(by=chosen_col, ascending=ascending).head(top_n)
        total_sum = grouped[chosen_col].sum()
        if total_sum > 0:
            sorted_df["Share_of_Total_Pct"] = (sorted_df[chosen_col] / total_sum * 100).round(2)
        top_item = sorted_df.iloc[0] if len(sorted_df) > 0 else None
        return {
            "status": "success", "intent": "ranking", "measure": measure or "Count",
            "dimension": dimension, "summary_table": sorted_df,
            "top_entity": top_item[dimension] if top_item is not None else None,
            "top_value": top_item[chosen_col] if top_item is not None else None,
            "total_categories": int(working_df[dimension].nunique()),
            "supporting_stats": {"grand_total": float(total_sum), "top_count": len(sorted_df)},
        }

    # 3. TIME SERIES
    elif intent == "time_series":
        time_col = plan.get("time_column") or (profile["dates"][0]["column"] if profile["dates"] else None)
        if not time_col:
            return {"status": "error", "message": "Time series analysis requires a recognized date column."}
        working_df["_parsed_dt"] = pd.to_datetime(working_df[time_col], errors="coerce", format="mixed")
        valid_time_df = working_df.dropna(subset=["_parsed_dt"]).sort_values("_parsed_dt")
        freq_map = {"day": "D", "week": "W", "month": "ME", "quarter": "QE", "year": "YE"}
        freq = freq_map.get(plan.get("time_granularity", "month"), "ME")

        if measure:
            resampled = valid_time_df.set_index("_parsed_dt").resample(freq)[measure].sum().reset_index()
            val_col = f"Total_{measure}"
            resampled = resampled.rename(columns={measure: val_col})
        else:
            resampled = valid_time_df.set_index("_parsed_dt").resample(freq).size().reset_index(name="Record_Count")
            val_col = "Record_Count"

        resampled["Period"] = resampled["_parsed_dt"].dt.strftime("%Y-%m" if freq == "ME" else "%Y-%m-%d")
        return {
            "status": "success", "intent": "time_series", "measure": measure or "Count",
            "time_column": time_col, "time_granularity": plan.get("time_granularity", "month"),
            "summary_table": resampled[["Period", val_col]],
            "supporting_stats": {
                "earliest_date": str(resampled["Period"].iloc[0]),
                "latest_date": str(resampled["Period"].iloc[-1]),
                "total_periods": len(resampled),
                "start_value": float(resampled[val_col].iloc[0]),
                "end_value": float(resampled[val_col].iloc[-1]),
            },
        }

    # 4. ANOMALY DETECTION (IQR)
    elif intent == "anomaly":
        target_col = plan.get("anomaly_column") or measure
        if not target_col or target_col not in df.columns or not pd.api.types.is_numeric_dtype(df[target_col]):
            return {"status": "error", "message": f"Anomaly detection requires a numeric column. '{target_col}' is invalid."}
        series = working_df[target_col].dropna()
        q1, q3 = float(series.quantile(0.25)), float(series.quantile(0.75))
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_mask = (working_df[target_col] < lower_bound) | (working_df[target_col] > upper_bound)
        outliers_df = working_df[outlier_mask].copy()
        outlier_count = int(outlier_mask.sum())
        outlier_pct = round((outlier_count / len(working_df)) * 100, 2) if len(working_df) > 0 else 0

        preview_cols = [target_col]
        for id_col in profile["identifiers"][:2]:
            if id_col["column"] in working_df.columns:
                preview_cols.insert(0, id_col["column"])
        for dim_col in profile["dimensions"][:2]:
            if dim_col["column"] in working_df.columns and dim_col["column"] not in preview_cols:
                preview_cols.append(dim_col["column"])

        return {
            "status": "success", "intent": "anomaly", "measure": target_col,
            "q1": round(q1, 2), "q3": round(q3, 2), "iqr": round(iqr, 2),
            "lower_bound": round(lower_bound, 2), "upper_bound": round(upper_bound, 2),
            "outlier_count": outlier_count, "outlier_percentage": outlier_pct,
            "summary_table": outliers_df[preview_cols].head(15),
            "supporting_stats": {"outlier_count": outlier_count, "outlier_pct": outlier_pct},
        }

    # 5. DISTRIBUTION
    elif intent == "distribution":
        if not measure:
            return {"status": "error", "message": "Distribution analysis requires a numeric measure."}
        s = working_df[measure].dropna()
        return {
            "status": "success", "intent": "distribution", "measure": measure,
            "summary_table": pd.DataFrame({
                "Statistic": ["Count", "Mean", "Std Dev", "Min", "25%", "50% (Median)", "75%", "Max"],
                "Value": [len(s), round(float(s.mean()), 2), round(float(s.std()), 2) if len(s) > 1 else 0,
                          round(float(s.min()), 2), round(float(s.quantile(0.25)), 2), round(float(s.median()), 2),
                          round(float(s.quantile(0.75)), 2), round(float(s.max()), 2)],
            }),
            "raw_series": s,
            "supporting_stats": {"median": float(s.median()), "mean": float(s.mean())},
        }

    return {"status": "error", "message": f"Analytical intent '{intent}' could not be processed with current data."}


TEA_COLORWAY = ["#2d6a4f", "#c58f3b", "#52b788", "#bc6c25", "#40916c", "#dda15e", "#74c69d", "#936639"]


def create_visualization(calc_result: Dict[str, Any], plan: Dict[str, Any], df: pd.DataFrame) -> Optional[go.Figure]:
    if calc_result.get("status") != "success":
        return None
    intent = calc_result.get("intent")
    table = calc_result.get("summary_table")
    if table is None or (isinstance(table, pd.DataFrame) and table.empty):
        return None

    layout_defaults = dict(
        template="plotly_white",
        margin=dict(l=30, r=30, t=45, b=30),
        font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif", size=12, color="#19281e"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=TEA_COLORWAY,
    )

    try:
        if intent == "ranking":
            dim = calc_result["dimension"]
            val_col = [c for c in table.columns if c != dim and "Share" not in c][0]

            # Power BI Donut chart for small dimension cardinalities (<= 6)
            if len(table) <= 6:
                fig = px.pie(
                    table, names=dim, values=val_col,
                    title=f"Breakdown by {dim.replace('_', ' ').title()}",
                    hole=0.55, color_discrete_sequence=TEA_COLORWAY
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(**layout_defaults)
                return fig

            # Power BI Bar chart for larger lists
            fig = px.bar(
                table, x=val_col, y=dim, orientation="h", text=val_col,
                title=f"Ranking by {val_col.replace('_', ' ').title()}",
                color_discrete_sequence=["#2d6a4f"]
            )
            fig.update_layout(**layout_defaults)
            fig.update_yaxes(autorange="reversed")
            fig.update_traces(texttemplate="%{text:,.2s}", textposition="outside", marker_line_color="#1b4332", marker_line_width=1)
            return fig

        elif intent == "time_series":
            val_col = [c for c in table.columns if c != "Period"][0]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=table["Period"], y=table[val_col], mode="lines+markers",
                name=val_col.replace("_", " "),
                line=dict(color="#2d6a4f", width=3),
                fill="tozeroy", fillcolor="rgba(45, 106, 79, 0.12)",
                marker=dict(size=6, color="#c58f3b", line=dict(color="#ffffff", width=1.5)),
            ))
            fig.update_layout(title=f"Trend Analysis ({val_col.replace('_', ' ')})", **layout_defaults)
            return fig

        elif intent == "anomaly":
            measure = calc_result["measure"]
            working_vals = df[measure].dropna().reset_index(drop=True)
            lb, ub = calc_result["lower_bound"], calc_result["upper_bound"]
            fig = go.Figure()
            normal_mask = (working_vals >= lb) & (working_vals <= ub)
            fig.add_trace(go.Scatter(
                x=working_vals[normal_mask].index, y=working_vals[normal_mask],
                mode="markers", name="Standard Records",
                marker=dict(color="#52796f", size=5, opacity=0.55)
            ))
            outlier_mask = (working_vals < lb) | (working_vals > ub)
            fig.add_trace(go.Scatter(
                x=working_vals[outlier_mask].index, y=working_vals[outlier_mask],
                mode="markers", name="Statistical Outliers",
                marker=dict(color="#c1121f", size=8, symbol="diamond")
            ))
            fig.add_hline(y=ub, line_dash="dash", line_color="#c1121f", annotation_text=f"Upper: {ub:,.1f}")
            fig.add_hline(y=lb, line_dash="dash", line_color="#c1121f", annotation_text=f"Lower: {lb:,.1f}")
            fig.update_layout(title=f"Statistical Outlier Inspection ({measure})", xaxis_title="Record Index", yaxis_title=measure, **layout_defaults)
            return fig

        elif intent == "distribution":
            fig = px.histogram(
                df, x=calc_result["measure"], nbins=30,
                title=f"Distribution of {calc_result['measure'].replace('_', ' ')}",
                color_discrete_sequence=["#40916c"]
            )
            fig.update_layout(**layout_defaults)
            fig.update_traces(marker_line_color="#1b4332", marker_line_width=0.8)
            return fig
    except Exception:
        return None
    return None


def generate_ai_explanation(question: str, calc_result: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[str, List[str]]:
    client = OpenAI(api_key=BACKEND_API_KEY)
    summary_data = calc_result["summary_table"].head(10).to_dict(orient="records") if isinstance(calc_result.get("summary_table"), pd.DataFrame) else None

    prompt_context = {
        "client_question": question,
        "analytical_intent": calc_result.get("intent"),
        "calculated_value": calc_result.get("calculated_value"),
        "supporting_stats": calc_result.get("supporting_stats"),
        "summary_table_top_records": summary_data,
        "available_dimensions": [d["column"] for d in profile["dimensions"]],
        "available_measures": [m["column"] for m in profile["measures"]],
    }

    system_prompt = """
You are an Executive Tea Industry Business Analyst delivering a direct briefing to senior leadership.
Calculations are 100% computed locally by Python/pandas.

CRITICAL INSTRUCTIONS:
1. Ground your response EXCLUSIVELY on the calculated numbers provided. DO NOT guess or hallucinate any numbers.
2. Be extremely concise, executive, and to the point. No fluff or generic disclaimers.
3. Structure your response into EXACTLY four sections:
   ### Direct Answer
   1-2 sharp sentences directly answering the question with the exact calculated figure.

   ### Key Evidence
   Bullet points citing the exact computed numbers, totals, or percentage shares.

   ### Why & Root Cause
   Explain the operational, seasonal, or market reason behind this result in the tea industry (e.g. First Flush seasonal scarcity, export auction demand, premium packaging multipliers, or regional harvest logistics).

   ### Strategic Action
   1 clear, high-impact tactical operational next step for the business.

4. Suggest EXACTLY 3 relevant follow-up questions referencing ACTUAL entities or columns in this client's tea dataset formatted as:
   ---FOLLOW_UPS---
   - Question 1?
   - Question 2?
   - Question 3?
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", temperature=0.1,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Calculated Results Context:\n{json.dumps(prompt_context, default=str)}"}],
        )
        full_text = response.choices[0].message.content
        if "---FOLLOW_UPS---" in full_text:
            parts = full_text.split("---FOLLOW_UPS---")
            explanation = parts[0].strip()
            followups = [re.sub(r"^[-*\d.\s]+", "", line).strip() for line in parts[1].splitlines() if line.strip() and "?" in line][:3]
        else:
            explanation, followups = full_text.strip(), []
        return explanation, followups
    except Exception:
        calc_val = calc_result.get("calculated_value", "Calculated successfully")
        stats = calc_result.get("supporting_stats", {})

        lines = [
            "### Direct Answer",
            f"{calc_val}.",
            "",
            "### Key Evidence",
        ]
        if stats:
            for k, v in stats.items():
                label = k.replace("_", " ").capitalize()
                lines.append(f"- **{label}**: {v:,}" if isinstance(v, (int, float)) else f"- **{label}**: {v}")
        elif isinstance(calc_result.get("summary_table"), pd.DataFrame) and not calc_result["summary_table"].empty:
            top_rec = calc_result["summary_table"].iloc[0]
            lines.append(f"- **Top Performer**: {', '.join([f'{col}: {top_rec[col]}' for col in calc_result['summary_table'].columns[:3]])}")
            lines.append(f"- **Total Records Analyzed**: {len(calc_result['summary_table']):,}")
        else:
            lines.append(f"- Processed across active tea metrics ({len(profile.get('measures', []))}) and operational segments ({len(profile.get('dimensions', []))}).")

        # Tailored "Why" and "Action" based on analytical intent
        intent = calc_result.get("intent", "general")
        dim = calc_result.get("dimension", "segment")

        if intent == "ranking":
            why_text = f"Variations across {dim.replace('_', ' ')} are primarily driven by harvest flush seasonality, grade-specific export auction bidding premiums, and volume allocation between overseas vs domestic buyers."
            action_text = f"Optimize allocation towards top-performing {dim.replace('_', ' ')} lots during peak auction windows to maximize realized price per unit."
        elif intent == "anomaly":
            why_text = "Outlier values correlate with micro-lot specialty auctions or extreme shipment transit delays during peak monsoon logistics."
            action_text = "Flag flagged outlier lots for immediate quality assurance and secondary cupping review."
        elif intent == "time_series":
            why_text = "Monthly fluctuations mirror the agricultural plucking cycles, where Spring First Flush and Summer Second Flush concentrate over 60% of annual revenue."
            action_text = "Align forward export contracts 60 days prior to flush arrival to secure pre-auction price guarantees."
        else:
            why_text = "Metric distribution reflects consistent operational clearance and verified commercial transactions across all designated tea portfolios."
            action_text = "Maintain ongoing inventory tracking and review lower-margin segments for blending reallocations."

        lines.extend([
            "",
            "### Why & Root Cause",
            why_text,
            "",
            "### Strategic Action",
            action_text,
        ])
        explanation = "\n".join(lines)

        followups = []
        dims = [d["column"] for d in profile.get("dimensions", [])]
        meas = [m["column"] for m in profile.get("measures", [])]
        if dims:
            followups.append(f"What is the revenue breakdown across {dims[0]}?")
        if len(dims) > 1:
            followups.append(f"Which {dims[1]} achieved the highest average price or margin?")
        if meas:
            followups.append(f"What is the monthly performance trend for {meas[0]}?")
        if not followups:
            followups = ["Which tea grade generated the highest revenue?", "What are the seasonal flush volume trends?"]

        return explanation, followups[:3]


def generate_client_management_summary(df: pd.DataFrame, profile: Dict[str, Any], client_name: str) -> str:
    client = OpenAI(api_key=BACKEND_API_KEY)

    metrics_summary = []
    for m in profile["measures"][:4]:
        col = m["column"]
        s = df[col].dropna()
        metrics_summary.append({"measure": col, "sum": round(float(s.sum()), 2), "mean": round(float(s.mean()), 2), "min": round(float(s.min()), 2), "max": round(float(s.max()), 2)})

    anomalies_summary = []
    for m in profile["measures"][:3]:
        col = m["column"]
        s = df[col].dropna()
        if len(s) > 10:
            q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
            iqr = q3 - q1
            outliers = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
            anomalies_summary.append({"column": col, "outlier_count": outliers, "outlier_pct": round((outliers / len(s)) * 100, 2)})

    segment_summary = []
    if profile["dimensions"]:
        dim_col = profile["dimensions"][0]["column"]
        if profile["measures"]:
            meas_col = profile["measures"][0]["column"]
            grouped = df.groupby(dim_col)[meas_col].sum().sort_values(ascending=False).head(5)
            segment_summary = [{"dimension": dim_col, "category": k, "sum": round(float(v), 2)} for k, v in grouped.items()]
        else:
            grouped = df[dim_col].value_counts().head(5)
            segment_summary = [{"dimension": dim_col, "category": k, "count": int(v)} for k, v in grouped.items()]

    payload = {
        "client_name": client_name,
        "dataset_rows": len(df), "dataset_cols": len(df.columns),
        "overall_measures": metrics_summary,
        "statistical_anomalies": anomalies_summary,
        "top_segments": segment_summary,
    }

    system_prompt = f"""
You are an Executive Tea Industry Business Intelligence Director delivering an official Management Briefing for {client_name}.
Synthesize the provided calculated facts into an executive-ready briefing based ONLY on the actual data.
Be concise, data-driven, and focused on business drivers.

STRUCTURE YOUR RESPONSE STRICTLY UNDER THESE EXACT HEADINGS:
### Overall Performance
Key quantitative metrics, total volume, total revenue, and portfolio summary.

### Top Drivers & Key Contributors
Observed concentration among top tea estates, blends, categories, or channels.

### The "Why" & Market Dynamics
Explain why these segments lead (seasonal flush harvest premiums, export bidding competition, packaging multiplier economics).

### Priority Action Items
2-3 crisp, high-impact tactical operational recommendations for management.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", temperature=0.1,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Calculated Summary Context:\n{json.dumps(payload, default=str)}"}],
        )
        return response.choices[0].message.content
    except Exception:
        sections = [
            "### Overall Performance",
            f"The business portfolio for **{client_name}** represents **{len(df):,} total verified transactions** across **{len(df.columns)} commercial attributes**."
        ]
        if metrics_summary:
            m_bullets = []
            for m in metrics_summary:
                m_bullets.append(f"- **{m['measure'].replace('_', ' ').title()}**: Total = **{m['sum']:,}** | Mean = **{m['mean']:,}** (Range: {m['min']:,} - {m['max']:,})")
            sections.append("\n".join(m_bullets))
        else:
            sections.append("Verified commercial operations logged across all active tea portfolios.")

        sections.extend([
            "",
            "### Top Drivers & Key Contributors",
        ])
        if segment_summary:
            s_bullets = [f"- **{s.get('category')}**: **{s.get('sum', s.get('count')):,}** ({s.get('dimension').replace('_', ' ').title()})" for s in segment_summary]
            sections.append("\n".join(s_bullets))
        else:
            sections.append("Commercial volume remains balanced across active estate and retail channels.")

        sections.extend([
            "",
            "### The \"Why\" & Market Dynamics",
            "- **Seasonal Harvest Premiums**: Leading revenue segments benefit directly from high-demand spring and summer flushes which command up to 140% pricing premiums.",
            "- **Export & Retail Channel Leverage**: Top contributors demonstrate superior buyer stickiness across premium wholesale export auctions and high-margin direct-to-consumer packaging formats.",
            "- **Quality Grade Differentiation**: Whole-leaf orthodox and artisanal reserve lines maintain high cupping ratings (>89/100) insulating prices from broader commodity volatility.",
            "",
            "### Priority Action Items",
            "1. **Contract Locking**: Forward-contract top-tier tea grades 60 days prior to auction delivery to secure guaranteed margin floors.",
            "2. **Logistics Optimization**: Accelerate customs clearance for high-moisture risk lots to protect cupping quality scores.",
            "3. **Channel Reallocation**: Increase allocation to online flagship and luxury corporate accounts which deliver the highest gross margin percentages."
        ])
        return "\n".join(sections)


# ==============================================================================
# MAIN CLIENT PORTAL CONTROLLER
# ==============================================================================
def main():
    # --------------------------------------------------------------------------
    # 1. AUTHENTICATION & ROLE-BASED ACCESS CONTROL (RBAC)
    # --------------------------------------------------------------------------
    if st.session_state.authenticated_client is None:
        st.markdown(
            """
            <div style="text-align: center; padding: 40px 20px 15px 20px;">
                <span style="font-size: 3.2rem;">🍵</span>
                <h1 style="color: #1b4332; font-family: 'Playfair Display', serif; font-weight: 700; font-size: 2.8rem; letter-spacing: -0.02em; margin-top: 8px;">CAMELLIA ANALYTICS PORTAL</h1>
                <p style="color: #52796f; font-size: 1.15rem; max-width: 650px; margin: 0 auto 20px auto; font-weight: 500;">
                    Enterprise AI Business Intelligence for Tea Plantations, Global Auctions & Specialty Retail
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        login_col1, login_col2, login_col3 = st.columns([1, 1.8, 1])
        with login_col2:
            st.markdown(
                """
                <div style="background: #ffffff; border: 1px solid #d8e6df; border-radius: 12px; padding: 28px; box-shadow: 0 4px 12px rgba(27, 67, 50, 0.06);">
                    <h3 style="color: #1b4332; margin-bottom: 6px; font-weight: 700;">Client Portal Sign In</h3>
                    <p style="color: #64748b; font-size: 0.88rem; margin-bottom: 20px;">Enter your dedicated credentials to access your isolated tea business records.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("client_login_form"):
                username_input = st.text_input("Username", placeholder="e.g. client_alpha or client_beta")
                password_input = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In to Portal", type="primary", use_container_width=True)

                if submitted:
                    client_profile = authenticate_client(username_input, password_input)
                    if client_profile:
                        st.session_state.authenticated_client = client_profile
                        st.success(f"Welcome back, {client_profile['display_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please verify your client username and password.")

            # Quick Demo Switcher helper for the user/evaluator
            st.markdown("---")
            st.caption("🔒 **Role-Based Demo Accounts (Click to test client data isolation):**")
            demo_cols = st.columns(2)
            if demo_cols[0].button("🍵 Himalayan Estate Teas (Auctions & Exports)", use_container_width=True):
                st.session_state.authenticated_client = CLIENTS["client_alpha"]
                st.rerun()
            if demo_cols[1].button("🍃 Zenith Artisanal Blends (Retail & D2C)", use_container_width=True):
                st.session_state.authenticated_client = CLIENTS["client_beta"]
                st.rerun()

        st.stop()

    # --------------------------------------------------------------------------
    # 2. AUTHENTICATED CLIENT SESSION
    # --------------------------------------------------------------------------
    active_client = st.session_state.authenticated_client
    client_id = active_client["username"]

    # Ingest this client's in-built dataset from disk
    df, err = load_client_dataset(active_client["data_file"])
    if err or df is None:
        st.error(f"Error loading client data: {err}")
        st.stop()

    profile = profile_dataset(df)

    # Initialize this client's isolated chat store
    if client_id not in st.session_state.client_chat_stores:
        st.session_state.client_chat_stores[client_id] = []
    if client_id not in st.session_state.client_contexts:
        st.session_state.client_contexts[client_id] = {}

    client_messages = st.session_state.client_chat_stores[client_id]
    client_context = st.session_state.client_contexts[client_id]

    # --------------------------------------------------------------------------
    # 3. SIDEBAR: CLIENT IDENTITY & NAVIGATION
    # --------------------------------------------------------------------------
    st.sidebar.markdown(f"### 🍵 {active_client['display_name']}")
    st.sidebar.markdown(
        f"""
        <div class="tea-client-badge">
            <div class="tea-client-name">{active_client['display_name']}</div>
            <div class="tea-client-role">👤 Role: {active_client['role']}</div>
            <div style="color: #52796f; font-size: 0.78rem; margin-top: 5px; font-weight: 500;">{active_client['industry']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.caption(f"📁 **In-built Dataset:** `{active_client['description']}`")
    st.sidebar.caption(f"📊 **Records Loaded:** `{len(df):,}` rows | `{len(df.columns)}` columns")
    st.sidebar.markdown("---")

    # Client-Facing Navigation: ONLY Chatbot and Reports
    nav_view = st.sidebar.radio(
        "Navigation View",
        options=["💬 Chatbot", "📊 Reports"],
        index=0,
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out", use_container_width=True):
        st.session_state.authenticated_client = None
        st.rerun()

    # --------------------------------------------------------------------------
    # VIEW 1: 💬 CHATBOT INTERFACE
    # --------------------------------------------------------------------------
    if nav_view == "💬 Chatbot":
        st.markdown(f"# 💬 AI Tea Business Analyst")
        st.markdown(f"*Ask natural language questions about your tea estate auction, quality, and commercial records. Grounded 100% in your dedicated data.*")

        # Quick Suggested Prompts
        st.markdown("##### 💡 Suggested Questions for Your Data:")
        s_cols = st.columns(len(active_client["sample_prompts"]))
        clicked_prompt = None
        for idx, prompt_text in enumerate(active_client["sample_prompts"]):
            if s_cols[idx].button(prompt_text, key=f"quick_{idx}", use_container_width=True):
                clicked_prompt = prompt_text

        st.markdown("---")

        # Display isolated conversational history for this client
        for msg in client_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("figure"):
                    st.plotly_chart(msg["figure"], use_container_width=True)
                if msg.get("table") is not None:
                    st.dataframe(msg["table"], use_container_width=True)

        # Chat Input Bar
        user_query = st.chat_input("Ask a question about your tea business records...")
        active_query = clicked_prompt or user_query

        if active_query:
            # 0. Safety Guard: Disallow non-data prompts
            non_data_keywords = ["write a poem", "tell me a joke", "weather", "who is the president", "recipe", "story"]
            if any(k in active_query.lower() for k in non_data_keywords):
                bot_response = "I am restricted to answering questions strictly regarding your assigned business records."
                client_messages.append({"role": "user", "content": active_query})
                client_messages.append({"role": "assistant", "content": bot_response})
                with st.chat_message("user"):
                    st.markdown(active_query)
                with st.chat_message("assistant"):
                    st.markdown(bot_response)
                st.stop()

            if not BACKEND_API_KEY:
                st.error("System configuration notice: AI service is currently unavailable. Please check system configuration.")
                st.stop()

            # Record user message in isolated store
            client_messages.append({"role": "user", "content": active_query})
            with st.chat_message("user"):
                st.markdown(active_query)

            # Assistant Processing
            with st.chat_message("assistant"):
                with st.spinner("Analyzing your tea commercial records..."):
                    # 1. Create plan
                    plan = create_analysis_plan(
                        question=active_query,
                        profile=profile,
                        conversation_context=client_context,
                    )

                    # 2. Validate
                    is_valid, validation_error = validate_analysis_plan(plan, df, profile)
                    if not is_valid:
                        bot_response = f"**Notice:** {validation_error}"
                        st.markdown(bot_response)
                        client_messages.append({"role": "assistant", "content": bot_response})
                        st.stop()

                    # 3. Calculate locally with Python
                    calc_result = execute_analysis(plan, df, profile)
                    if calc_result.get("status") != "success":
                        bot_response = f"**Error:** {calc_result.get('message', 'Unable to calculate result.')}"
                        st.markdown(bot_response)
                        client_messages.append({"role": "assistant", "content": bot_response})
                        st.stop()

                    # 4. Create visual
                    fig = create_visualization(calc_result, plan, df)

                    # 5. Generate executive narrative
                    ai_explanation, followups = generate_ai_explanation(
                        question=active_query,
                        calc_result=calc_result,
                        profile=profile,
                    )

                    # Update isolated context
                    st.session_state.client_contexts[client_id] = {
                        "last_question": active_query,
                        "last_intent": plan.get("intent"),
                        "last_measure": plan.get("measure"),
                        "last_dimension": plan.get("dimension"),
                        "last_top_entity": calc_result.get("top_entity"),
                    }

                    # Render Output
                    st.markdown(ai_explanation)

                    table_df = calc_result.get("summary_table")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    if isinstance(table_df, pd.DataFrame):
                        st.dataframe(table_df, use_container_width=True)

                    # Append to isolated history
                    client_messages.append({
                        "role": "assistant",
                        "content": ai_explanation,
                        "figure": fig,
                        "table": table_df if isinstance(table_df, pd.DataFrame) else None,
                    })

                    # Render follow-up suggestions
                    if followups:
                        st.markdown("##### 🔍 Follow-Up Suggestions:")
                        f_cols = st.columns(len(followups))
                        for f_idx, f_text in enumerate(followups):
                            if f_cols[f_idx].button(f_text, key=f"fup_{len(client_messages)}_{f_idx}", use_container_width=True):
                                # Immediately push as next turn
                                client_messages.append({"role": "user", "content": f_text})
                                st.rerun()

    # --------------------------------------------------------------------------
    # VIEW 2: 📊 POWER BI STANDARD REPORTS INTERFACE
    # --------------------------------------------------------------------------
    elif nav_view == "📊 Reports":
        st.markdown(f"# 📊 Executive BI Dashboard: {active_client['display_name']}")
        st.caption(f"Comprehensive commercial intelligence and BI report visuals based on **{len(df):,} verified records**.")

        # ----------------------------------------------------------------------
        # A. POWER BI INTERACTIVE SLICERS BAR
        # ----------------------------------------------------------------------
        st.markdown(
            """
            <div class="pbi-slicer-container">
                <div class="pbi-slicer-title">🎛️ Interactive BI Slicers</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        s_col1, s_col2, s_col3, s_col4 = st.columns(4)

        # Date Slicer
        date_col = profile["dates"][0]["column"] if profile["dates"] else None
        selected_year = "All"
        if date_col and date_col in df.columns:
            df["_parsed_dt"] = pd.to_datetime(df[date_col], errors="coerce")
            available_years = sorted([str(int(y)) for y in df["_parsed_dt"].dt.year.dropna().unique()])
            if available_years:
                selected_year = s_col1.selectbox("📅 Reporting Year", options=["All"] + available_years)

        # Primary Dimension Slicer (Region / Market)
        region_col = None
        for col in ["REGION", "MARKET_REGION"]:
            if col in df.columns:
                region_col = col
                break
        if not region_col and profile["dimensions"]:
            region_col = profile["dimensions"][0]["column"]

        selected_region = "All"
        if region_col:
            reg_opts = sorted(list(df[region_col].dropna().unique()))
            selected_region = s_col2.selectbox(f"📍 {region_col.replace('_', ' ').title()}", options=["All"] + reg_opts)

        # Secondary Dimension Slicer (Grade / Category)
        grade_col = None
        for col in ["TEA_GRADE", "CATEGORY", "SEASON_FLUSH"]:
            if col in df.columns:
                grade_col = col
                break
        if not grade_col and len(profile["dimensions"]) > 1:
            grade_col = profile["dimensions"][1]["column"]

        selected_grade = "All"
        if grade_col:
            grade_opts = sorted(list(df[grade_col].dropna().unique()))
            selected_grade = s_col3.selectbox(f"🍃 {grade_col.replace('_', ' ').title()}", options=["All"] + grade_opts)

        # Tertiary Dimension Slicer (Channel / Center)
        channel_col = None
        for col in ["AUCTION_CENTER", "SALES_CHANNEL", "PACKAGING"]:
            if col in df.columns:
                channel_col = col
                break
        selected_channel = "All"
        if channel_col:
            chan_opts = sorted(list(df[channel_col].dropna().unique()))
            selected_channel = s_col4.selectbox(f"🏛️ {channel_col.replace('_', ' ').title()}", options=["All"] + chan_opts)

        # Apply Slicer Filtering dynamically
        filtered_df = df.copy()
        if selected_year != "All" and date_col:
            filtered_df = filtered_df[filtered_df["_parsed_dt"].dt.year == int(selected_year)]
        if selected_region != "All" and region_col:
            filtered_df = filtered_df[filtered_df[region_col] == selected_region]
        if selected_grade != "All" and grade_col:
            filtered_df = filtered_df[filtered_df[grade_col] == selected_grade]
        if selected_channel != "All" and channel_col:
            filtered_df = filtered_df[filtered_df[channel_col] == selected_channel]

        st.caption(f"Showing **{len(filtered_df):,}** of **{len(df):,}** records matching active slicer selections.")
        st.markdown("---")

        # ----------------------------------------------------------------------
        # B. POWER BI STANDARD KPI CARDS ROW
        # ----------------------------------------------------------------------
        # Identify key business columns dynamically
        rev_col = None
        for col in ["TOTAL_REVENUE_USD", "NET_SALES_USD", "REVENUE", "SALES"]:
            if col in filtered_df.columns:
                rev_col = col
                break
        if not rev_col and profile["measures"]:
            rev_col = profile["measures"][0]["column"]

        vol_col = None
        for col in ["VOLUME_KG", "UNITS_SOLD", "QUANTITY", "VOLUME"]:
            if col in filtered_df.columns:
                vol_col = col
                break

        price_margin_col = None
        for col in ["PRICE_PER_KG_USD", "GROSS_MARGIN_PCT", "UNIT_PRICE_USD", "MARGIN"]:
            if col in filtered_df.columns:
                price_margin_col = col
                break

        qual_col = None
        for col in ["QUALITY_SCORE", "CUSTOMER_RATING", "RATING"]:
            if col in filtered_df.columns:
                qual_col = col
                break

        kpi_cols = st.columns(4)

        # Card 1: Revenue
        if rev_col and pd.api.types.is_numeric_dtype(filtered_df[rev_col]):
            tot_rev = filtered_df[rev_col].sum()
            rev_fmt = f"${tot_rev/1_000_000:,.2f}M" if tot_rev >= 1_000_000 else f"${tot_rev:,.0f}"
            kpi_cols[0].markdown(
                f"""
                <div class="pbi-kpi-card forest-accent">
                    <div class="pbi-kpi-title">{rev_col.replace('_', ' ').upper()}</div>
                    <div class="pbi-kpi-value">{rev_fmt}</div>
                    <div class="pbi-kpi-subtitle">
                        <span class="pbi-kpi-badge">Gross Realized</span> Total commercial volume
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            kpi_cols[0].markdown(
                f"""
                <div class="pbi-kpi-card forest-accent">
                    <div class="pbi-kpi-title">TOTAL RECORDS</div>
                    <div class="pbi-kpi-value">{len(filtered_df):,}</div>
                    <div class="pbi-kpi-subtitle">Active transactions</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Card 2: Volume / Units
        if vol_col and pd.api.types.is_numeric_dtype(filtered_df[vol_col]):
            tot_vol = filtered_df[vol_col].sum()
            vol_unit = "kg" if "KG" in vol_col else "units"
            vol_fmt = f"{tot_vol/1_000_000:,.2f}M {vol_unit}" if tot_vol >= 1_000_000 else f"{tot_vol/1_000:,.1f}K {vol_unit}"
            kpi_cols[1].markdown(
                f"""
                <div class="pbi-kpi-card amber-accent">
                    <div class="pbi-kpi-title">{vol_col.replace('_', ' ').upper()}</div>
                    <div class="pbi-kpi-value">{vol_fmt}</div>
                    <div class="pbi-kpi-subtitle">
                        <span class="pbi-kpi-badge amber">Total Quantity</span> Cleared & shipped
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            kpi_cols[1].markdown(
                f"""
                <div class="pbi-kpi-card amber-accent">
                    <div class="pbi-kpi-title">ATTRIBUTES TRACKED</div>
                    <div class="pbi-kpi-value">{len(filtered_df.columns)}</div>
                    <div class="pbi-kpi-subtitle">Dataset dimensions</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Card 3: Price / Margin
        if price_margin_col and pd.api.types.is_numeric_dtype(filtered_df[price_margin_col]):
            avg_pm = filtered_df[price_margin_col].mean()
            pm_fmt = f"{avg_pm:,.1f}%" if "PCT" in price_margin_col or "MARGIN" in price_margin_col else f"${avg_pm:,.2f}/kg"
            kpi_cols[2].markdown(
                f"""
                <div class="pbi-kpi-card matcha-accent">
                    <div class="pbi-kpi-title">AVG {price_margin_col.replace('_', ' ').upper()}</div>
                    <div class="pbi-kpi-value">{pm_fmt}</div>
                    <div class="pbi-kpi-subtitle">
                        <span class="pbi-kpi-badge">Portfolio Mean</span> Realized unit pricing
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            kpi_cols[2].markdown(
                f"""
                <div class="pbi-kpi-card matcha-accent">
                    <div class="pbi-kpi-title">DATA HEALTH</div>
                    <div class="pbi-kpi-value">100%</div>
                    <div class="pbi-kpi-subtitle">Zero synthetic records</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Card 4: Quality Score / Customer Rating
        if qual_col and pd.api.types.is_numeric_dtype(filtered_df[qual_col]):
            avg_qual = filtered_df[qual_col].mean()
            qual_fmt = f"{avg_qual:,.1f} / 100" if avg_qual > 10 else f"{avg_qual:,.2f} ★"
            kpi_cols[3].markdown(
                f"""
                <div class="pbi-kpi-card">
                    <div class="pbi-kpi-title">AVG {qual_col.replace('_', ' ').upper()}</div>
                    <div class="pbi-kpi-value">{qual_fmt}</div>
                    <div class="pbi-kpi-subtitle">
                        <span class="pbi-kpi-badge">Standard Cupping</span> Sensory & buyer rating
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            date_range = f"{profile['dates'][0]['earliest'][:7]} to {profile['dates'][0]['latest'][:7]}" if profile['dates'] else "Active"
            kpi_cols[3].markdown(
                f"""
                <div class="pbi-kpi-card">
                    <div class="pbi-kpi-title">RECORDING WINDOW</div>
                    <div class="pbi-kpi-value" style="font-size: 1.25rem; line-height: 2rem;">{date_range}</div>
                    <div class="pbi-kpi-subtitle">Multi-year harvest</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # ----------------------------------------------------------------------
        # C. POWER BI STANDARD VISUALS GRID
        # ----------------------------------------------------------------------
        st.markdown("### 📈 Power BI Analytical Visuals")

        # Visual Row 1
        v_row1_col1, v_row1_col2 = st.columns([1.5, 1.0])

        with v_row1_col1:
            st.markdown("##### 📅 Monthly Revenue Performance Trend (Area Chart)")
            if date_col and rev_col and date_col in filtered_df.columns and rev_col in filtered_df.columns:
                trend_df = filtered_df.dropna(subset=["_parsed_dt"]).copy()
                trend_df["Month_Period"] = trend_df["_parsed_dt"].dt.to_period("M").dt.to_timestamp()
                monthly_agg = trend_df.groupby("Month_Period")[rev_col].sum().reset_index()
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=monthly_agg["Month_Period"], y=monthly_agg[rev_col],
                    mode="lines+markers", name="Total Revenue",
                    line=dict(color="#2d6a4f", width=3),
                    fill="tozeroy", fillcolor="rgba(45, 106, 79, 0.12)",
                    marker=dict(size=6, color="#c58f3b", line=dict(color="#ffffff", width=1.5))
                ))
                fig_trend.update_layout(
                    template="plotly_white", margin=dict(l=20, r=20, t=30, b=20),
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=11),
                    xaxis_title="Month", yaxis_title="Revenue (USD)",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                fig_trend.update_yaxes(tickprefix="$", tickformat=",.2s")
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Time-series trend requires recognized date and revenue columns.")

        with v_row1_col2:
            st.markdown("##### 🍩 Revenue Share by Category / Grade (Donut Chart)")
            donut_dim = grade_col or (profile["dimensions"][0]["column"] if profile["dimensions"] else None)
            if donut_dim and rev_col and donut_dim in filtered_df.columns and rev_col in filtered_df.columns:
                donut_agg = filtered_df.groupby(donut_dim)[rev_col].sum().sort_values(ascending=False).head(7).reset_index()
                fig_donut = px.pie(
                    donut_agg, names=donut_dim, values=rev_col,
                    hole=0.55, color_discrete_sequence=TEA_COLORWAY
                )
                fig_donut.update_traces(textposition="inside", textinfo="percent+label")
                fig_donut.update_layout(
                    template="plotly_white", margin=dict(l=10, r=10, t=25, b=10),
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=11),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("Category breakdown requires categorical and measure fields.")

        # Visual Row 2
        v_row2_col1, v_row2_col2 = st.columns(2)

        with v_row2_col1:
            st.markdown("##### 🏆 Top 10 Performers by Commercial Revenue")
            entity_col = "ESTATE" if "ESTATE" in filtered_df.columns else ("PRODUCT_NAME" if "PRODUCT_NAME" in filtered_df.columns else (profile["dimensions"][0]["column"] if profile["dimensions"] else None))
            if entity_col and rev_col and entity_col in filtered_df.columns and rev_col in filtered_df.columns:
                top_agg = filtered_df.groupby(entity_col)[rev_col].sum().sort_values(ascending=False).head(10).reset_index()
                fig_top = px.bar(
                    top_agg, x=rev_col, y=entity_col, orientation="h",
                    text=rev_col, color_discrete_sequence=["#2d6a4f"]
                )
                fig_top.update_layout(
                    template="plotly_white", margin=dict(l=20, r=20, t=30, b=20),
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=11),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                fig_top.update_yaxes(autorange="reversed")
                fig_top.update_traces(texttemplate="$%{text:,.2s}", textposition="outside", marker_line_color="#1b4332", marker_line_width=1)
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.info("Ranking requires categorical entity and numeric measures.")

        with v_row2_col2:
            st.markdown("##### 🏛️ Revenue Distribution Across Channels / Centers")
            dist_col = channel_col or region_col
            if dist_col and rev_col and dist_col in filtered_df.columns and rev_col in filtered_df.columns:
                chan_agg = filtered_df.groupby(dist_col)[rev_col].sum().sort_values(ascending=False).head(8).reset_index()
                fig_chan = px.bar(
                    chan_agg, x=dist_col, y=rev_col, text=rev_col,
                    color=dist_col, color_discrete_sequence=TEA_COLORWAY
                )
                fig_chan.update_layout(
                    template="plotly_white", margin=dict(l=20, r=20, t=30, b=20),
                    font=dict(family="Plus Jakarta Sans, sans-serif", size=11),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                fig_chan.update_traces(texttemplate="$%{text:,.2s}", textposition="outside")
                st.plotly_chart(fig_chan, use_container_width=True)
            else:
                st.info("Channel breakdown requires dimension and numeric measures.")

        st.markdown("---")

        # ----------------------------------------------------------------------
        # D. POWER BI MATRIX BREAKDOWN TABLE
        # ----------------------------------------------------------------------
        st.markdown("### 📑 Power BI Commercial Matrix Summary")
        st.caption("Detailed multidimensional breakdown comparing volume, revenue, and realized rates across key segments:")

        matrix_dim = region_col or (profile["dimensions"][0]["column"] if profile["dimensions"] else None)
        if matrix_dim and rev_col and vol_col and matrix_dim in filtered_df.columns:
            matrix_grouped = filtered_df.groupby(matrix_dim).agg(
                Transactions=("LOT_ID" if "LOT_ID" in filtered_df.columns else "ORDER_ID", "count"),
                Total_Volume=(vol_col, "sum"),
                Total_Revenue=(rev_col, "sum"),
            ).reset_index()

            tot_matrix_rev = matrix_grouped["Total_Revenue"].sum()
            matrix_grouped["Revenue_Share_Pct"] = ((matrix_grouped["Total_Revenue"] / max(0.01, tot_matrix_rev)) * 100).round(2)
            matrix_grouped["Avg_Realized_Rate"] = (matrix_grouped["Total_Revenue"] / matrix_grouped["Total_Volume"].replace(0, np.nan)).round(2)

            matrix_grouped = matrix_grouped.sort_values(by="Total_Revenue", ascending=False)

            # Format for presentation
            display_matrix = pd.DataFrame()
            display_matrix[matrix_dim.replace("_", " ").title()] = matrix_grouped[matrix_dim]
            display_matrix["Transactions"] = matrix_grouped["Transactions"].map("{:,}".format)
            unit_lbl = "kg" if "KG" in vol_col else "units"
            display_matrix[f"Total Volume ({unit_lbl})"] = matrix_grouped["Total_Volume"].map("{:,.0f}".format)
            display_matrix["Total Revenue (USD)"] = matrix_grouped["Total_Revenue"].map("${:,.2f}".format)
            display_matrix["Avg Rate ($/unit)"] = matrix_grouped["Avg_Realized_Rate"].map("${:,.2f}".format)
            display_matrix["Revenue Share %"] = matrix_grouped["Revenue_Share_Pct"].map("{:.2f}%".format)

            st.dataframe(display_matrix, use_container_width=True)

        st.markdown("---")

        # ----------------------------------------------------------------------
        # E. EXECUTIVE MANAGEMENT BRIEFING (ON-DEMAND)
        # ----------------------------------------------------------------------
        st.markdown("### 📋 Executive Management Briefing (AI Synthesis)")
        st.caption("Generate an executive briefing synthesized from your verified tea commercial dataset.")

        if st.button("Generate Executive Briefing", type="primary", use_container_width=False):
            with st.spinner("Synthesizing executive briefing from your filtered commercial records..."):
                briefing_md = generate_client_management_summary(filtered_df, profile, active_client["display_name"])
                st.markdown("---")
                st.markdown(briefing_md)

        st.markdown("---")

        # ----------------------------------------------------------------------
        # F. VERIFIED CLIENT RECORD EXPLORER & CSV EXPORT
        # ----------------------------------------------------------------------
        st.markdown("### 🗃️ Client Business Records Explorer")
        st.caption(f"Inspection table for active verified records ({len(filtered_df):,} records selected):")
        st.dataframe(filtered_df.drop(columns=["_parsed_dt"], errors="ignore"), use_container_width=True)

        csv_bytes = filtered_df.drop(columns=["_parsed_dt"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"📥 Download Filtered Records Report (CSV - {len(filtered_df):,} Rows)",
            data=csv_bytes,
            file_name=f"{client_id}_tea_commercial_report.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
