from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--excel", required=True)
    p.add_argument("--value", required=True, help="要查找的字符串（如放射编号）")
    args = p.parse_args()

    excel_path = Path(args.excel)
    df = pd.read_excel(excel_path, dtype=str, engine="openpyxl").fillna("")
    cols = [str(c) for c in df.columns]

    print("columns(first 30):", cols[:30])

    value = str(args.value)

    # 先在所有列里做 contains
    hits = []
    for c in cols:
        try:
            n = int(df[c].astype(str).str.contains(value, na=False).sum())
        except Exception:
            n = 0
        if n:
            hits.append((c, n))

    if not hits:
        print("NO HIT for", value)
        return 0

    hits.sort(key=lambda x: x[1], reverse=True)
    print("HITS:")
    for c, n in hits[:20]:
        print(f"  {c}\tcount={n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
