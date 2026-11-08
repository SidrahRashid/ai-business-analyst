"""
TEST SUITE: FASTAPI API ENDPOINTS & INTEGRATION
===============================================
Tests:
1. /api/system/architecture
2. /api/glossary GET and POST
3. /api/chat with custom business jargon
4. /api/chat with complex window function intent
5. /api/reports/kpis and /charts backward compatibility
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from server import app

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

client = TestClient(app)

def test_all():
    print("\n--- [API TEST 1] System Architecture Endpoint ---")
    r = client.get("/api/system/architecture", headers={"X-Client-Id": "client_alpha"})
    assert r.status_code == 200, f"Status code: {r.status_code}, {r.text}"
    data = r.json()
    assert data["scalability_engine"]["olap_database"].startswith("DuckDB")
    assert "FileSharedCacheProvider" in data["cache_architecture"]["type"] or "CacheProvider" in data["cache_architecture"]["type"]
    print(f"[PASS] Architecture Status: {data['status']}, OLAP: {data['scalability_engine']['olap_database']}")

    print("\n--- [API TEST 2] Dynamic Business Glossary Endpoints ---")
    r = client.get("/api/glossary", headers={"X-Client-Id": "client_alpha"})
    assert r.status_code == 200
    glossary = r.json()
    assert "realized gross inflow" in glossary.get("aliases", {})
    print(f"[PASS] Retrieved active glossary with {len(glossary.get('aliases', {}))} aliases")

    # Add custom term
    r = client.post("/api/glossary/terms", json={
        "term": "test enterprise payload",
        "target_column": "VOLUME_KG"
    }, headers={"X-Client-Id": "client_alpha"})
    assert r.status_code == 200
    print("[PASS] Dynamic glossary POST verified")

    # Remove custom term
    r = client.delete("/api/glossary/terms/test enterprise payload", headers={"X-Client-Id": "client_alpha"})
    assert r.status_code == 200
    print("[PASS] Dynamic glossary DELETE verified")

    print("\n--- [API TEST 3] Chat with Custom Jargon ---")
    r = client.post("/api/chat/query", json={
        "question": "What is the gross turnover by tea garden?",
        "conversation_context": {}
    }, headers={"X-Client-Id": "client_alpha"})
    assert r.status_code == 200, f"Error {r.status_code}: {r.text}"
    chat_res = r.json()
    assert chat_res["status"] == "success"
    print(f"[PASS] Chat query with corporate jargon succeeded! Answer: {chat_res['answer'][:120]}...")

    print("\n--- [API TEST 4] Chat with Complex Window Function ---")
    r = client.post("/api/chat/query", json={
        "question": "Show cumulative running total of revenue over time",
        "conversation_context": {}
    }, headers={"X-Client-Id": "client_alpha"})
    assert r.status_code == 200, f"Error {r.status_code}: {r.text}"
    cum_res = r.json()
    assert cum_res["status"] == "success"
    assert "Cumulative" in cum_res["answer"] or "cumulative" in cum_res["answer"]
    print(f"[PASS] Complex window function executed! Answer: {cum_res['answer'][:120]}...")

    print("\n--- [API TEST 5] Backward Compatibility (Reports & Charts) ---")
    r_kpi = client.get("/api/reports/kpis", headers={"X-Client-Id": "client_alpha"})
    assert r_kpi.status_code == 200
    print("[PASS] /api/reports/kpis OK")

    r_charts = client.get("/api/reports/charts", headers={"X-Client-Id": "client_alpha"})
    assert r_charts.status_code == 200
    print("[PASS] /api/reports/charts OK")

    print("\n--- [API TEST 6] Multi-Turn Pronoun Resolution ---")
    # Turn 1: Ask for top estate
    t1 = client.post("/api/chat/query", json={
        "question": "Which tea estate generated the highest revenue?",
        "conversation_context": {}
    }, headers={"X-Client-Id": "client_alpha"})
    assert t1.status_code == 200
    ctx = t1.json().get("conversation_context", {})
    assert "last_entity" in ctx or "last_dimension" in ctx, f"Context should have last_entity: {ctx}"
    print(f"[PASS] Turn 1 captured context entity: {ctx.get('last_entity')}")

    # Turn 2: Follow up with pronoun "its volume"
    t2 = client.post("/api/chat/query", json={
        "question": "What was its total volume in kgs?",
        "conversation_context": ctx
    }, headers={"X-Client-Id": "client_alpha"})
    assert t2.status_code == 200
    ans_t2 = t2.json()["answer"]
    assert "kgs" in ans_t2 or "volume" in ans_t2.lower()
    print(f"[PASS] Turn 2 pronoun resolution succeeded! Answer: {ans_t2[:100]}...")

    print("\n========================================================")
    print("ALL API ENDPOINTS & ENTERPRISE UPGRADES 100% OPERATIONAL!")
    print("========================================================")

if __name__ == "__main__":
    test_all()
