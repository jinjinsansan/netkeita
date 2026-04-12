import json, urllib.request

print("=== ゾンニッヒ (中山11R #1) ===")
data = json.loads(urllib.request.urlopen("http://localhost:5002/api/horse-detail/20260404-%E4%B8%AD%E5%B1%B1-11/1", timeout=30).read())
for r in data.get("recent_runs", []):
    print(f"  {r.get('race_name','?')} | class={r.get('class_name','')}")

print("\n=== フェルアフリーゼ (中山1R #3) ===")
data2 = json.loads(urllib.request.urlopen("http://localhost:5002/api/horse-detail/20260404-%E4%B8%AD%E5%B1%B1-1/3", timeout=30).read())
for r in data2.get("recent_runs", []):
    print(f"  {r.get('race_name','?')} | class={r.get('class_name','')}")
