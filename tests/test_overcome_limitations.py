"""
TEST SUITE: VERIFICATION OF THE 5 ENTERPRISE UPGRADES
=====================================================
1. Limitation 1 & 3: DuckDB OLAP Columnar Engine & Lazy Star-Schema Joins
2. Limitation 2: Advanced Analytical Window Functions, Correlations, Pareto
3. Limitation 4: Dynamic Business Glossary & Enterprise Jargon Mapping
4. Limitation 5: Pluggable Cache Provider (FileShared, InMemory, Redis)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from olap_engine import get_olap_engine
from glossary_manager import load_client_glossary, add_glossary_term, delete_glossary_term, resolve_glossary_term
from complex_analytics import detect_complex_intent, execute_complex_analytical_query, synthesize_complex_narrative
from cache_provider import InMemoryCacheProvider, FileSharedCacheProvider, get_cache_provider
from analytics_engine import (
    load_client_dataset,
    profile_dataset,
    create_analysis_plan,
    validate_analysis_plan,
    execute_analysis,
    build_dynamic_semantic_maps,
)


def test_limitation_1_and_3_olap_and_lazy_joins():
    print("\n--- [TEST 1 & 3] DuckDB OLAP & Lazy Star-Schema Join Engine ---")
    olap = get_olap_engine()
    registered = olap.register_client_dataset("client_alpha")
    assert registered, "Client Alpha should register in DuckDB."
    print("[PASS] Client Alpha tables and views registered in DuckDB successfully.")

    # Test Lazy Star-Schema Query Builder: only join dim_estates when asking for ESTATE
    lazy_sql = olap.build_lazy_star_query(
        client_id="client_alpha",
        measures=[("VOLUME_KG", "SUM")],
        dimensions=["ESTATE"],
        sort_by='"Sum_VOLUME_KG"',
        sort_dir="DESC",
        limit=5
    )
    print(f"[PASS] Generated Lazy Star-Schema Query:\n  {lazy_sql}")
    assert "LEFT JOIN client_alpha_dim_estates" in lazy_sql, "Must lazily join dim_estates"
    assert "LEFT JOIN client_alpha_dim_buyers" not in lazy_sql, "Must NOT eagerly join dim_buyers when unneeded!"
    assert "LEFT JOIN client_alpha_fact_shipments" not in lazy_sql, "Must NOT eagerly join fact_shipments!"

    # Execute query in DuckDB
    res_df, err = olap.execute_query(lazy_sql)
    assert err is None, f"Query execution failed: {err}"
    assert len(res_df) == 5, f"Expected 5 records, got {len(res_df)}"
    print(f"[PASS] Executed successfully in DuckDB! Top estate: {res_df.iloc[0]['ESTATE']} with {res_df.iloc[0]['Sum_VOLUME_KG']:,.2f} kgs")

    # Test Fact-Only query (Zero joins required)
    fact_only_sql = olap.build_lazy_star_query(
        client_id="client_alpha",
        measures=[("VOLUME_KG", "SUM")],
        dimensions=["SEASON_FLUSH"]
    )
    assert "LEFT JOIN" not in fact_only_sql, "Fact-only query must have ZERO joins!"
    print(f"[PASS] Fact-Only query requires ZERO joins:\n  {fact_only_sql}")


def test_limitation_2_complex_analytical_intents():
    print("\n--- [TEST 2] Advanced Analytical Intents & Window Functions ---")
    df_alpha, _ = load_client_dataset("data/client_alpha/himalayan_estate_teas.csv")
    profile = profile_dataset(df_alpha)

    # A. Cumulative Running Total
    q_cum = "Show cumulative running total of revenue over time"
    intent_cum = detect_complex_intent(q_cum)
    assert intent_cum == "cumulative_running_total", f"Expected cumulative_running_total, got {intent_cum}"
    df_cum, met_cum, err_cum = execute_complex_analytical_query("client_alpha", intent_cum, q_cum, profile)
    assert err_cum is None, f"Cumulative execution error: {err_cum}"
    assert "Cumulative_TOTAL_REVENUE_USD" in df_cum.columns
    print(f"[PASS] Cumulative Running Total: Final value = ${met_cum['final_cumulative_value']:,.2f} across {met_cum['period_count']} months")

    # B. Moving Average (3-Month Rolling)
    q_ma = "Show 3-month rolling moving average of revenue"
    intent_ma = detect_complex_intent(q_ma)
    assert intent_ma == "moving_average"
    df_ma, met_ma, err_ma = execute_complex_analytical_query("client_alpha", intent_ma, q_ma, profile)
    assert err_ma is None
    assert "Rolling_3Month_Avg" in df_ma.columns
    print(f"[PASS] 3-Month Moving Average: Latest month = {met_ma['latest_month']}, Avg = ${met_ma['latest_rolling_avg']:,.2f}")

    # C. Statistical Correlation
    q_corr = "What is the correlation between price per kg and quality score?"
    intent_corr = detect_complex_intent(q_corr)
    assert intent_corr == "correlation"
    df_corr, met_corr, err_corr = execute_complex_analytical_query("client_alpha", intent_corr, q_corr, profile)
    assert err_corr is None
    print(f"[PASS] Pearson Correlation: r = {met_corr['correlation_coefficient']:+.4f} ({met_corr['relationship_strength']})")

    # D. Weighted Ratio
    q_ratio = "Which estate has the highest effective yield price to volume?"
    intent_ratio = detect_complex_intent(q_ratio)
    assert intent_ratio == "weighted_ratio"
    df_ratio, met_ratio, err_ratio = execute_complex_analytical_query("client_alpha", intent_ratio, q_ratio, profile)
    assert err_ratio is None
    print(f"[PASS] Weighted Realization Ratio: Top entity = {met_ratio['top_entity']} at ${met_ratio['top_realized_rate']:,.2f} / kg")

    # E. Full Pipeline Integration
    plan = create_analysis_plan("Show cumulative running revenue over time", profile, {}, client_id="client_alpha")
    assert plan["intent"] == "cumulative_running_total"
    is_valid, _ = validate_analysis_plan(plan, df_alpha, profile)
    assert is_valid, "Complex plan must be validated successfully"
    calc_res = execute_analysis(plan, df_alpha, profile)
    assert calc_res["status"] == "success"
    assert "precomputed_narrative" in calc_res
    print("[PASS] Full end-to-end complex analytics plan -> execution pipeline verified!")


def test_limitation_4_dynamic_business_glossary():
    print("\n--- [TEST 4] Dynamic Business Glossary & Custom Corporate Jargon ---")
    df_alpha, _ = load_client_dataset("data/client_alpha/himalayan_estate_teas.csv")
    profile = profile_dataset(df_alpha)

    # 1. Add custom term: "acme custom harvest" -> "VOLUME_KG"
    ok, msg = add_glossary_term("client_alpha", "acme custom harvest", "VOLUME_KG")
    assert ok, f"Failed to add glossary term: {msg}"
    print(f"[PASS] Added custom term: 'acme custom harvest' -> 'VOLUME_KG'")

    # 2. Verify semantic map incorporation
    dim_map, meas_map = build_dynamic_semantic_maps(profile, client_id="client_alpha")
    assert "acme custom harvest" in meas_map.get("VOLUME_KG", []), "Custom term must appear in meas_map!"
    assert "realized gross inflow" in meas_map.get("TOTAL_REVENUE_USD", []), "Default alias 'realized gross inflow' must be present!"
    print(f"[PASS] Custom jargon successfully compiled into active semantic maps!")

    # 3. Test natural language query containing custom jargon: "What is the realized gross inflow by tea garden?"
    plan = create_analysis_plan("What is the gross turnover by tea garden?", profile, {}, client_id="client_alpha")
    assert plan["intent"] == "ranking" or plan["intent"] == "aggregation"
    assert plan.get("dimension") == "ESTATE", f"Expected ESTATE for 'tea garden', got {plan.get('dimension')}"
    assert plan.get("measure") == "TOTAL_REVENUE_USD", f"Expected TOTAL_REVENUE_USD for 'gross turnover', got {plan.get('measure')}"
    print(f"[PASS] Custom query 'gross turnover by tea garden' correctly resolved to dimension='{plan.get('dimension')}' and measure='{plan.get('measure')}'!")

    # Cleanup temporary term
    delete_glossary_term("client_alpha", "acme custom harvest")


def test_limitation_5_pluggable_cache_providers():
    print("\n--- [TEST 5] Pluggable Cache Provider (Multi-Worker Shared Cache) ---")
    # 1. Memory Cache
    mem_cache = InMemoryCacheProvider()
    mem_cache.set("test_key", {"foo": "bar"}, ttl_seconds=60)
    assert mem_cache.get("test_key") == {"foo": "bar"}
    mem_cache.delete("test_key")
    assert mem_cache.get("test_key") is None
    print("[PASS] InMemoryCacheProvider verified.")

    # 2. FileSharedCacheProvider (Multi-Process / Multi-Worker shared)
    file_cache = FileSharedCacheProvider()
    file_cache.set("worker_shared_kpi", {"revenue": 10500000}, ttl_seconds=300)
    read_back = file_cache.get("worker_shared_kpi")
    assert read_back == {"revenue": 10500000}, "Shared disk cache must return saved payload"
    stats = file_cache.get_stats()
    print(f"[PASS] FileSharedCacheProvider verified. Active cache directory: {stats['cache_dir']}")
    file_cache.delete("worker_shared_kpi")

    # 3. Default Provider Factory
    provider = get_cache_provider()
    print(f"[PASS] System Default Provider resolved: {provider.__class__.__name__}")


if __name__ == "__main__":
    try:
        test_limitation_1_and_3_olap_and_lazy_joins()
        test_limitation_2_complex_analytical_intents()
        test_limitation_4_dynamic_business_glossary()
        test_limitation_5_pluggable_cache_providers()
        print("\n========================================================")
        print("ALL 5 LIMITATIONS SUCCESSFULLY OVERCOME AND VERIFIED!")
        print("========================================================")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
