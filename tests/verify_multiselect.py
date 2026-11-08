import urllib.request
import urllib.parse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_multiselect():
    try:
        from fastapi.testclient import TestClient
        from server import app
        client = TestClient(app)
        use_testclient = True
    except Exception:
        use_testclient = False

    def get(endpoint, qs=''):
        if use_testclient:
            url = f'/api/reports/{endpoint}' + (f'?{qs}' if qs else '')
            res = client.get(url, headers={'Authorization': 'Bearer client_alpha'})
            return res.json()
        qs_safe = urllib.parse.quote(qs, safe='=&,')
        url = f'http://127.0.0.1:8000/api/reports/{endpoint}?{qs_safe}'
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer client_alpha'})
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode())

    # 1. Total records
    all_kpis = get('kpis')
    tot = all_kpis['record_count']
    print(f"Total Alpha records: {tot}")

    # 2. Month multi-select verification
    mar = get('kpis', 'month=March')['record_count']
    apr = get('kpis', 'month=April')['record_count']
    mar_apr = get('kpis', 'month=March,April')['record_count']
    print(f"March count: {mar}, April count: {apr}, March+April count: {mar_apr}")
    assert mar_apr == mar + apr, f"Expected {mar + apr}, got {mar_apr}"
    print("[PASS] Month multi-select accurately filters and sums dataset")

    # 3. Year multi-select verification
    y23 = get('kpis', 'year=2023')['record_count']
    y24 = get('kpis', 'year=2024')['record_count']
    y23_24 = get('kpis', 'year=2023,2024')['record_count']
    print(f"2023 count: {y23}, 2024 count: {y24}, 2023+2024 count: {y23_24}")
    assert y23_24 == y23 + y24, f"Expected {y23 + y24}, got {y23_24}"
    print("[PASS] Year multi-select accurately filters and sums dataset")

    # 4. Region/Category multi-select verification
    darj = get('kpis', 'category=Darjeeling')['record_count']
    assam = get('kpis', 'category=Upper Assam')['record_count']
    darj_assam = get('kpis', 'category=Darjeeling,Upper Assam')['record_count']
    print(f"Darjeeling: {darj}, Upper Assam: {assam}, Darjeeling+Upper Assam: {darj_assam}")
    assert darj_assam == darj + assam, f"Expected {darj + assam}, got {darj_assam}"
    print("[PASS] Region multi-select accurately filters and sums dataset")

    # 5. Charts endpoint with multi-select
    charts = get('charts', 'month=March,April&year=2023,2024')
    assert 'monthly_trend' in charts
    assert 'category_share' in charts
    assert 'ranking_leaders' in charts
    assert 'channel_distribution' in charts
    print("[PASS] Charts endpoint returns valid payloads with multi-select slicers")

    # 6. Matrix endpoint with multi-select
    matrix = get('matrix', 'category=Darjeeling,Upper Assam')
    assert len(matrix['rows']) > 0
    row_names = [r['name'] for r in matrix['rows']]
    print(f"[PASS] Matrix endpoint reflects multi-select categories: {len(matrix['rows'])} segments ({row_names[:4]}...)")

    # 7. Briefing endpoint with multi-select
    briefing = get('briefing', 'month=March,April')
    assert 'executive_summary' in briefing
    assert 'macro_drivers' in briefing
    print("[PASS] Briefing endpoint successfully generated for multi-select slicers")

    print("\nALL BACKEND MULTI-SELECT TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_multiselect()
