import sys
sys.path.insert(0, "/opt/dlogic/backend")
from services.viewlogic_data_manager import get_viewlogic_data_manager

dm = get_viewlogic_data_manager()
hd = dm.get_horse_data("フェルアフリーゼ")
if hd and hd.get("races"):
    r = hd["races"][0]
    # Print ALL key-value pairs to find class info
    for k in sorted(r.keys()):
        v = r[k]
        if v and str(v).strip():
            print(f"  {k}: '{v}'")
