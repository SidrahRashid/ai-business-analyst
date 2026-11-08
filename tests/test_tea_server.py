"""
TEST SCRIPT FOR CAMELLIA TEA ATELIER FASTAPI SERVER
Tests all endpoints using FastAPI TestClient (no live port binding required).
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def run_tests():
    print("=== STARTING CAMELLIA TEA ATELIER SERVER TESTS ===")
    
    # 1. Test Index Page
    res = client.get("/")
    assert res.status_code == 200, f"Index failed: {res.status_code}"
    assert "CAMELLIA ATELIER" in res.text, "Index does not contain Camellia Atelier brand"
    print("[PASS] Index page served successfully.")

    # 2. Test Login client_alpha
    res = client.post("/api/auth/login", json={"username": "client_alpha", "password": "himalayan_secret"})
    assert res.status_code == 200, f"Login alpha failed: {res.text}"
    data = res.json()
    assert data["client_id"] == "client_alpha"
    assert "Himalayan" in data["client_name"]
    token_alpha = data["token"]
    print("[PASS] client_alpha login successful.")

    # 3. Test Login client_beta
    res = client.post("/api/auth/login", json={"username": "client_beta", "password": "zenith_secret"})
    assert res.status_code == 200, f"Login beta failed: {res.text}"
    data_beta = res.json()
    assert data_beta["client_id"] == "client_beta"
    assert "Zenith" in data_beta["client_name"]
    token_beta = data_beta["token"]
    print("[PASS] client_beta login successful.")

    # 4. Test Slicers Filters for client_alpha (including new Month and Tertiary slicers)
    res = client.get("/api/reports/filters", headers={"Authorization": f"Bearer {token_alpha}"})
    assert res.status_code == 200
    filters = res.json()
    assert filters["category_label"] == "Region"
    assert "Darjeeling" in filters["categories"]
    assert len(filters["years"]) >= 2
    assert "months" in filters and len(filters["months"]) == 12
    assert "March" in filters["months"]
    assert filters["tertiary_label"] == "Harvest Flush"
    assert "First Flush (Spring)" in filters["tertiary"]
    print(f"[PASS] Slicers for alpha loaded: {len(filters['categories'])} regions, {len(filters['secondary'])} grades, {len(filters['months'])} months, {len(filters['tertiary'])} flushes.")

    # 5. Test KPIs for client_alpha (GET & POST, both unfiltered and with Month + Flush slicers)
    res_kpi_get = client.get("/api/reports/kpis?year=All", headers={"Authorization": f"Bearer {token_alpha}"})
    assert res_kpi_get.status_code == 200
    kpis = res_kpi_get.json()
    assert kpis["record_count"] == 4800
    assert "revenue" in kpis["kpis"]
    assert "volume" in kpis["kpis"]
    
    # Test with Month and Harvest Flush slicer applied
    res_kpi_filtered = client.get("/api/reports/kpis?year=2024&month=March&tertiary=First+Flush+%28Spring%29", headers={"Authorization": f"Bearer {token_alpha}"})
    assert res_kpi_filtered.status_code == 200
    kpis_filt = res_kpi_filtered.json()
    assert 0 < kpis_filt["record_count"] < 4800
    print(f"[PASS] KPIs for alpha: Total={kpis['record_count']}, Filtered(2024+March+FirstFlush)={kpis_filt['record_count']} lots, Revenue={kpis_filt['kpis']['revenue']['value']}.")

    # 6. Test Charts for client_alpha
    res_charts = client.get("/api/reports/charts?year=All", headers={"Authorization": f"Bearer {token_alpha}"})
    assert res_charts.status_code == 200
    charts = res_charts.json()
    assert len(charts["monthly_trend"]["labels"]) > 0
    assert len(charts["category_share"]["labels"]) > 0
    assert len(charts["ranking_leaders"]["labels"]) > 0
    assert len(charts["channel_distribution"]["labels"]) > 0
    print(f"[PASS] Charts for alpha: {len(charts['monthly_trend']['labels'])} months trend, {len(charts['ranking_leaders']['labels'])} ranking leaders.")

    # 7. Test Matrix for client_alpha
    res_matrix = client.get("/api/reports/matrix?year=All", headers={"Authorization": f"Bearer {token_alpha}"})
    assert res_matrix.status_code == 200
    matrix = res_matrix.json()
    assert len(matrix["rows"]) > 0
    print(f"[PASS] Matrix for alpha: {len(matrix['rows'])} segments.")

    # 8. Test Records for client_alpha
    res_records = client.get("/api/reports/records?limit=5", headers={"Authorization": f"Bearer {token_alpha}"})
    assert res_records.status_code == 200
    recs = res_records.json()["records"]
    assert len(recs) == 5
    print(f"[PASS] Audited records for alpha: {len(recs)} sampled rows with columns: {list(recs[0].keys())[:4]}...")

    # 9. Test Executive Briefing for client_alpha
    res_briefing = client.get("/api/reports/briefing", headers={"Authorization": f"Bearer {token_alpha}"})
    assert res_briefing.status_code == 200
    briefing = res_briefing.json()
    assert "executive_summary" in briefing
    assert len(briefing["macro_drivers"]) > 0
    print("[PASS] Executive briefing for alpha synthesized successfully.")

    # 10. Test Chatbot Query for client_alpha
    res_chat = client.post(
        "/api/chat/query",
        json={"question": "What is the total auction revenue and volume?"},
        headers={"Authorization": f"Bearer {token_alpha}"}
    )
    assert res_chat.status_code == 200
    chat_out = res_chat.json()
    assert chat_out["status"] == "success"
    assert len(chat_out["answer"]) > 0
    assert len(chat_out["evidence"]) > 0
    print("[PASS] Chatbot response for alpha verified:")
    print(f"   Direct Answer: {chat_out['answer']}")
    print(f"   Key Evidence: {chat_out['evidence']}")
    print(f"   Why & Root Cause: {chat_out['why_root_cause']}")
    print(f"   Strategic Action: {chat_out['action']}")

    # 11. Test Chatbot Query for client_beta (Retail client)
    res_chat_beta = client.post(
        "/api/chat/query",
        json={"question": "Which product category generated the highest net sales?"},
        headers={"Authorization": f"Bearer {token_beta}"}
    )
    assert res_chat_beta.status_code == 200
    chat_beta_out = res_chat_beta.json()
    assert chat_beta_out["status"] == "success"
    assert len(chat_beta_out["answer"]) > 0
    print("[PASS] Chatbot response for beta verified:")
    print(f"   Direct Answer: {chat_beta_out['answer']}")

    print("\n[SUCCESS] ALL 11 TESTS PASSED WITH 100% ACCURACY!")

if __name__ == "__main__":
    run_tests()
