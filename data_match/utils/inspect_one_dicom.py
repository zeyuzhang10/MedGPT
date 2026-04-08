from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# 允许两种运行方式：
# 1) 推荐：python -m dicom_dataset_tools.inspect_one_dicom
# 2) 兼容：python dicom_dataset_tools/inspect_one_dicom.py
_this_file = Path(__file__).resolve()
_pkg_dir = _this_file.parent
if _pkg_dir.name == "dicom_dataset_tools":
    _root_dir = _pkg_dir.parent
    if str(_root_dir) not in sys.path:
        sys.path.insert(0, str(_root_dir))

from dicom_dataset_tools.dicom_pipeline.dicom_utils import extract_meta, read_dicom


def main() -> int:
    p = argparse.ArgumentParser(description="读取单个 DICOM，打印可用于匹配 Excel 的关键信息")
    p.add_argument("--dicom", required=True, help="DICOM 文件路径")
    p.add_argument("--show-tags", action="store_true", help="额外打印更多 tag 名称")
    args = p.parse_args()

    path = Path(args.dicom)
    ds = read_dicom(path, stop_before_pixels=True)
    meta = extract_meta(ds)

    print("=== 核心字段（建议用来匹配 Excel）===")
    print(json.dumps(meta.__dict__, ensure_ascii=False, indent=2, default=str))

    if args.show_tags:
        print("\n=== Top-level tags（截断显示）===")
        keys = []
        for elem in ds:
            try:
                keys.append((elem.tag, elem.keyword, str(elem.value)[:80]))
            except Exception:
                pass
        for tag, keyword, value in keys[:80]:
            print(f"{tag}\t{keyword}\t{value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
