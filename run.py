"""Tạo business plan tuần cho từng giám sát (1 file Excel/giám sát/mô hình).

    python3 run.py                       # tuần kế tiếp, mô hình kết hợp (mặc định)
    python3 run.py --week 2026-11-09     # chỉ định thứ Hai của tuần
    python3 run.py --model all           # kethop | m1 | m2 | m3 | all
    python3 run.py --gs "Kim Ngân"       # chỉ 1 giám sát
"""
import argparse
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bp import metrics, model_combined, model_drivertree, model_merch, model_ogsm  # noqa: E402

MODELS = {"kethop": model_combined, "m1": model_drivertree, "m2": model_ogsm, "m3": model_merch}


def slug(s):
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", help="Thứ Hai đầu tuần kế hoạch, YYYY-MM-DD")
    ap.add_argument("--model", default="kethop", choices=["all", *MODELS],
                    help="kethop (mặc định) | m1 | m2 | m3 | all")
    ap.add_argument("--gs", help="Tên giám sát")
    ap.add_argument("--out", default=str(ROOT / "output"))
    ap.add_argument("--allow-gaps", action="store_true", help="vẫn chạy khi dữ liệu bán thiếu ngày")
    a = ap.parse_args()

    ws = date.fromisoformat(a.week) if a.week else None
    if ws and ws.weekday() != 0:
        sys.exit("--week phải là ngày thứ Hai")
    print("Đang tải & tính số liệu…")
    ctx = metrics.build(ws, a.allow_gaps)
    print(f"Dữ liệu bán đến {ctx.as_of}, tồn kho {ctx.inv_snapshot}; tuần {ctx.week_label} "
          f"({ctx.week_start}→{ctx.week_end}); {len(ctx.stores)} cửa hàng")

    groups = {}
    for s in ctx.stores:
        groups.setdefault(s["gs"], []).append(s)
    if a.gs:
        groups = {k: v for k, v in groups.items() if k == a.gs}

    chosen = MODELS if a.model == "all" else {a.model: MODELS[a.model]}
    for key, mod in chosen.items():
        d = Path(a.out) / ctx.week_label / mod.NAME
        d.mkdir(parents=True, exist_ok=True)
        for gs, stores in sorted(groups.items()):
            p = d / f"BP_{ctx.week_label}_{key.upper()}_{slug(gs)}.xlsx"
            mod.render(ctx, gs, stores, p)
            print(f"  ✓ {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}  ({len(stores)} CH)")


if __name__ == "__main__":
    main()
