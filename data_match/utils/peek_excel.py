from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--excel", required=True)
    p.add_argument("--col", default="放射编号")
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--no-stats", action="store_true")
    args = p.parse_args()

    df = pd.read_excel(Path(args.excel), dtype=str, engine="openpyxl").fillna("")
    col = args.col
    if col not in df.columns:
        print("available columns:", list(df.columns)[:50])
        raise SystemExit(f"column not found: {col}")

    s = df[col].astype(str)
    print("rows:", len(df))
    print(f"{col} sample:")
    for v in s.head(args.n).tolist():
        print(v)

    if args.no_stats:
        return 0

    # 打印一些统计：长度分布
    lens = s.map(lambda x: len(x.strip()))
    print("length stats:")
    print(lens.describe())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
