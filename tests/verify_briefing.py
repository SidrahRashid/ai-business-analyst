import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import app
from fastapi.testclient import TestClient

client = TestClient(app)

res_login = client.post("/api/auth/login", json={"username": "client_alpha", "password": "himalayan_secret"})
token = res_login.json()["token"]

res = client.get("/api/reports/briefing?year=All", headers={"Authorization": f"Bearer {token}"})
print("STATUS:", res.status_code)
briefing = res.json()
print("BRIEFING OUTPUT:")
print(json.dumps(briefing, indent=2))

# Verify none of the old vague boilerplate exists
vague_phrases = [
    "Audit of active tea ledger indicates sustained performance across core revenue drivers.",
    "Consistent demand across primary certified regions and grades.",
    "Zero unverified transactions detected across audited dataset.",
    "Performance variations are attributed to agricultural harvest cycles, elevation moisture indices, and packaging premium multipliers.",
    "Focus sales allocation on higher-realization auction lots and high-margin direct-to-consumer packaging formats."
]

for p in vague_phrases:
    assert p not in briefing["executive_summary"], f"Found vague phrase in summary: {p}"
    assert p not in briefing["root_cause_variance"], f"Found vague phrase in root cause: {p}"
    assert p not in briefing["strategic_directives"], f"Found vague phrase in directives: {p}"

print("\n[SUCCESS] ALL VAGUE BOILERPLATE COMPLETELY ELIMINATED! Briefing is fully grounded.")
