"""Check which NAR knowledge files are loaded and which contain which horses."""
import sys, json, os
sys.path.insert(0, "/opt/dlogic/backend")

# Check what NAR knowledge files exist
print("=== NAR Knowledge Files ===")
locations = [
    "/opt/dlogic/backend/data/",
    "/opt/dlogic/backend/",
    "/opt/dlogic/backend/scripts/",
]
for loc in locations:
    if os.path.isdir(loc):
        for f in sorted(os.listdir(loc)):
            if "nar" in f.lower() or "nankan" in f.lower():
                fp = os.path.join(loc, f)
                if os.path.isfile(fp):
                    size_mb = os.path.getsize(fp) / 1024 / 1024
                    print(f"  {fp}: {size_mb:.1f}MB")

# Try to load the LocalViewLogicEngineV2 and check its data
print("\n=== LocalViewLogicEngineV2 ===")
try:
    from services.local_viewlogic_engine_v2 import LocalViewLogicEngineV2
    e = LocalViewLogicEngineV2()
    print(f"  Engine loaded: {e}")
    
    # Get data manager
    if hasattr(e, "data_manager"):
        dm = e.data_manager
        print(f"  Data manager: {dm}")
        if hasattr(dm, "knowledge_data") and dm.knowledge_data:
            horses = dm.knowledge_data.get("horses", {})
            print(f"  Total horses in knowledge: {len(horses)}")
            # Sample horses
            keys = list(horses.keys())[:3]
            print(f"  Sample keys: {keys}")
    
    # Test specific horses from NAR races
    test_horses = [
        ("パワームーブ", "水沢1R #1"),
        ("メイショウヨンク", "高知11R #1"),
        ("モズグランプリ", "佐賀11R #1"),
    ]
    
    print("\n=== Horse lookups ===")
    for name, label in test_horses:
        h = e.get_horse_history(name)
        races = h.get("races", [])
        print(f"  {label} {name}: {len(races)} races, total={h.get('total_races','-')}")
        if races:
            r = races[0]
            print(f"    first: {r}")
except Exception as ex:
    import traceback
    print(f"  ERROR: {ex}")
    traceback.print_exc()

# Check NAR jockey knowledge
print("\n=== NAR Jockey Data ===")
try:
    from services.local_jockey_analyzer import LocalJockeyAnalyzer
    ja = LocalJockeyAnalyzer()
    print(f"  Loaded")
    # Test a NAR jockey
    for jname in ["坂井瑛音", "佐原秀泰", "林悠翔"]:
        try:
            data = ja.get_jockey_data(jname) if hasattr(ja, "get_jockey_data") else None
            print(f"  {jname}: {bool(data)}")
        except Exception as e:
            print(f"  {jname}: ERROR {e}")
except Exception as ex:
    print(f"  NAR jockey analyzer not found: {ex}")
    # Try alternate
    import glob
    nar_jockey_files = glob.glob("/opt/dlogic/backend/**/all_nar_jockey*.json", recursive=True)
    print(f"  NAR jockey files: {nar_jockey_files[:3]}")
