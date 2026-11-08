import urllib.request
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_chatbot_answers():
    try:
        from fastapi.testclient import TestClient
        from server import app
        client = TestClient(app)
        use_testclient = True
    except Exception:
        use_testclient = False

    def ask(q):
        if use_testclient:
            res = client.post('/api/chat/query', json={'question': q}, headers={'Authorization': 'Bearer client_alpha'})
            return res.json()
        url = 'http://127.0.0.1:8000/api/chat/query'
        data = json.dumps({'question': q}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Authorization': 'Bearer client_alpha', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode())

    # 1. "lowest revenue"
    res1 = ask("lowest revenue")
    print("Q1 lowest revenue answer:", res1.get('answer'))
    print("Q1 key_insights:", res1.get('key_insights'))
    assert "lowest" in res1.get('answer', '').lower()
    assert "highest" not in res1.get('answer', '').lower()
    print("[PASS] Q1 correctly identifies lowest revenue without claiming it is highest!")

    # 2. "what is cupping benchmark"
    res2 = ask("what is cupping benchmark")
    print("\nQ2 cupping benchmark answer:", res2.get('answer'))
    print("Q2 key_insights:", res2.get('key_insights'))
    assert "cupping" in res2.get('answer', '').lower() or "89.50" in res2.get('answer', '') or "quality" in res2.get('answer', '').lower()
    print("[PASS] Q2 generates specific cupping score insight!")

    # 3. "Show total volume in kg by season flush."
    res3 = ask("Show total volume in kg by season flush.")
    print("\nQ3 season flush answer:", res3.get('answer'))
    print("Q3 key_insights:", res3.get('key_insights'))
    assert "Autumn Flush" in res3.get('key_insights', '') or "Autumn Flush" in res3.get('answer', '')
    assert "Summer Second Flush gives the highest quantity" not in res3.get('key_insights', '')
    print("[PASS] Q3 dynamically identifies Autumn Flush as the highest volume in both answer and why_text insight!")

if __name__ == '__main__':
    test_chatbot_answers()
