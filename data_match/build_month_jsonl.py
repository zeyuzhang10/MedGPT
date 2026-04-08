from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import shutil
import uuid
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


# 允许两种运行方式：
# 1) 推荐：python -m dicom_dataset_tools.build_month_jsonl
# 2) 兼容：python dicom_dataset_tools/build_month_jsonl.py
_this_file = Path(__file__).resolve()
_pkg_dir = _this_file.parent
if _pkg_dir.name == "dicom_dataset_tools":
    _root_dir = _pkg_dir.parent
    if str(_root_dir) not in sys.path:
        sys.path.insert(0, str(_root_dir))

from dicom_pipeline.dicom_utils import (
    export_png,
    extract_meta,
    is_probably_dicom,
    is_too_large,
    read_dicom,
)
from dicom_pipeline.excel_utils import build_index, match_row


def setup_logger(root: Path, month: str, test: bool) -> logging.Logger:
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"run_{ts}_{month}{'_test' if test else ''}.log"
    log_path = logs_dir / name

    logger = logging.getLogger(f"dicom_build_{month}_{ts}")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s")

    fh = logging.FileHandler(str(log_path), encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)

    logger.info("log_path=%s", log_path)
    return logger


def iter_candidate_files(root_dir: Path) -> Iterable[Path]:
    # os.walk 在 Windows 大目录下通常比 Path.rglob 更快且更早产出结果
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            yield Path(dirpath) / name


def _get_tqdm():
    try:
        from tqdm import tqdm  # type: ignore

        return tqdm
    except Exception:
        return None


def collect_candidates(
    *,
    dicom_dir: Path,
    aggressive_scan: bool,
    max_mb: int,
    test: bool,
    sample: int,
    seed: int,
) -> tuple[list[Path], int]:
    """收集候选 DICOM 文件。

    - 非测试模式：尽可能收集所有候选（用于正式跑全量）
    - 测试模式：不做全量收集；找到足够的 sample 条就提前停止（满足“只采样而非先收集全部”）

    返回 (candidates, scanned_files)
    """

    rng = random.Random(seed)
    tqdm = _get_tqdm()

    # 正式模式：收集全部候选（可能很多）
    if not test:
        candidates: list[Path] = []
        scanned_files = 0
        pbar = tqdm(total=None, desc=f"scan month={dicom_dir.name}", unit="file") if tqdm is not None else None
        try:
            for f in iter_candidate_files(dicom_dir):
                scanned_files += 1
                if pbar is not None:
                    pbar.update(1)
                    if scanned_files % 2000 == 0:
                        pbar.set_postfix(found=len(candidates))
                if is_too_large(f, max_mb):
                    continue
                if is_probably_dicom(f, aggressive=aggressive_scan):
                    candidates.append(f)
        finally:
            if pbar is not None:
                pbar.set_postfix(found=len(candidates))
                pbar.close()
        return candidates, scanned_files

    # 测试模式：
    # 目标不是“扫到前 N 个文件”，而是尽量从不同的顶层目录（如 1..31 日）里随机抽样，
    # 这样更不容易全部落在同一个 PatientID/同一个检查批次。
    # 同时我们会收集一个更大的候选池（pool），提高命中 Excel 可匹配记录的概率。
    pool = min(max(sample * 50, sample), 5000)

    top_dirs = [p for p in dicom_dir.iterdir() if p.is_dir()]
    rng.shuffle(top_dirs)

    candidates = []
    scanned_files = 0

    pbar = tqdm(total=None, desc=f"scan month={dicom_dir.name} (test)", unit="file") if tqdm is not None else None

    # 每个顶层目录最多取这么多条，保证分散
    max_per_bucket = max(1, min(5, sample // 4 or 1))

    def _walk_dir(d: Path, limit: int | None) -> None:
        nonlocal scanned_files
        taken = 0
        for f in iter_candidate_files(d):
            scanned_files += 1
            if pbar is not None:
                pbar.update(1)
                if scanned_files % 1000 == 0:
                    pbar.set_postfix(pool=len(candidates))
            if is_too_large(f, max_mb):
                continue
            if not is_probably_dicom(f, aggressive=aggressive_scan):
                continue
            candidates.append(f)
            taken += 1
            if len(candidates) >= pool:
                return
            if limit is not None and taken >= limit:
                return

    # 第一轮：分桶抽样
    for d in top_dirs:
        _walk_dir(d, max_per_bucket)
        if len(candidates) >= pool:
            break

    # 兜底：如果候选还是不够（比如目录结构不规则），再全目录补齐
    if len(candidates) < min(pool, sample * 5):
        _walk_dir(dicom_dir, None)

    if pbar is not None:
        pbar.set_postfix(pool=len(candidates))
        pbar.close()

    rng.shuffle(candidates)
    return candidates[:pool], scanned_files


def load_existing_max_idx(jsonl_path: Path, month: str) -> int:
    if not jsonl_path.exists():
        return 0
    max_n = 0
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    idx = str(obj.get("idx", ""))
                    if idx.startswith(f"{month}-"):
                        tail = idx.split("-", 1)[1]
                        n = int(tail)
                        max_n = max(max_n, n)
                except Exception:
                    continue
    except Exception:
        return 0
    return max_n


def ordered_record(*, idx: str, image_path: str, excel_row: dict[str, Any], dicom_meta: dict[str, Any]) -> dict[str, Any]:
    # 关键字段优先放前面
    priority_keys = [
        "影像学诊断",
        "影像学表现",
        "设备类型",
        "设备",
        "诊断",
        "表现",
    ]

    out: dict[str, Any] = {}
    out["idx"] = idx
    out["image_path"] = image_path

    # 优先写 Excel 的关键文本
    for k in priority_keys:
        if k in excel_row and k not in out:
            out[k] = excel_row.get(k, "")

    # 写入 Excel 全字段
    for k, v in excel_row.items():
        if k in out:
            continue
        out[k] = v

    # 写入 DICOM 的有用字段
    out["dicom_meta"] = dicom_meta

    return out


def main() -> int:
    p = argparse.ArgumentParser(description="按月份目录扫描 DICOM，导出 PNG 并与 Excel 匹配，写出 jsonl")
    p.add_argument("--root", required=True, help="数据集根目录（如 F:\\\\）")
    p.add_argument("--month", required=True, help="月份子目录名（如 4 或 12）")
    p.add_argument("--excel", default="", help="手动指定 Excel 路径（默认 root/excel/{month}.xlsx）")
    p.add_argument("--test", action="store_true", help="测试模式：输出命名带 _test 且只采样")
    p.add_argument("--sample", type=int, default=20, help="测试模式采样数量")
    p.add_argument("--seed", type=int, default=42, help="采样随机种子")
    p.add_argument("--fuzz-threshold", type=float, default=0.90, help="相似度阈值（0-1）")
    p.add_argument("--day-tolerance", type=int, default=1, help="日期允许误差天数")
    p.add_argument("--aggressive-scan", action="store_true", help="更激进地把无扩展名文件也当 DICOM 尝试")
    p.add_argument("--max-mb", type=int, default=512, help="跳过超大文件（MB），避免卡死")
    args = p.parse_args()

    # Windows 下常见误用：传入 "F:" 会变成“当前盘符相对路径”，导致写到 F:logs 之类。
    root_str = str(args.root).strip().strip('"').strip("'")
    if re.fullmatch(r"[A-Za-z]:", root_str):
        root_str = root_str + "\\"
    root = Path(root_str)
    month = str(args.month)

    dicom_dir = root / month
    if not dicom_dir.exists():
        raise FileNotFoundError(f"月份目录不存在: {dicom_dir}")

    excel_path = Path(args.excel) if args.excel else (root / "excel" / f"{month}.xlsx")
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel 不存在: {excel_path}（可用 --excel 手动指定）")

    logger = setup_logger(root, month, args.test)
    logger.info("root=%s", root)
    logger.info("dicom_dir=%s", dicom_dir)
    logger.info("excel_path=%s", excel_path)

    index = build_index(excel_path)
    logger.info("excel_key_columns patient=%s accession=%s time=%s", index.patient_col, index.accession_col, index.time_col)

    out_jsonl = root / (f"{month}_test.jsonl" if args.test else f"{month}.jsonl")
    image_root = root / (f"{month}_image_test" if args.test else f"{month}_image")
    image_root.mkdir(parents=True, exist_ok=True)

    tmp_root = image_root / "_tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)

    start_n = load_existing_max_idx(out_jsonl, month)
    next_n = start_n + 1
    logger.info("resume_from=%d", start_n)

    # 收集候选路径：测试模式不全量扫描，找到 sample 条就停
    candidates, total_files = collect_candidates(
        dicom_dir=dicom_dir,
        aggressive_scan=args.aggressive_scan,
        max_mb=args.max_mb,
        test=args.test,
        sample=args.sample,
        seed=args.seed,
    )

    logger.info("scanned_files=%d probable_dicoms=%d", total_files, len(candidates))

    # 处理阶段只处理 sample 条（测试）或全部候选（正式）
    to_process = candidates
    if args.test:
        rng = random.Random(args.seed)
        if len(to_process) > args.sample:
            to_process = rng.sample(to_process, args.sample)
        logger.info("test_mode sample=%d actual=%d seed=%d", args.sample, len(to_process), args.seed)

    total_dicom_read_ok = 0
    total_png_ok = 0
    total_excel_matched = 0
    total_written = 0

    tqdm = _get_tqdm()
    iterator = (
        tqdm(to_process, total=len(to_process), desc=f"process month={month}{' (test)' if args.test else ''}", unit="dicom")
        if tqdm
        else to_process
    )

    with out_jsonl.open("a", encoding="utf-8") as jf:
        for path in iterator:
            # 1) 读 DICOM（不先读像素）
            try:
                ds = read_dicom(path, stop_before_pixels=True)
                meta = extract_meta(ds)
                total_dicom_read_ok += 1
            except Exception as e:
                logger.warning("dicom_read_fail\t%s\t%s", path, repr(e))
                continue

            # 2) Excel 匹配
            try:
                excel_row = match_row(
                    index,
                    patient_id=meta.patient_id,
                    accession_number=meta.accession_number,
                    study_dt=meta.study_datetime,
                    fuzz_threshold=args.fuzz_threshold,
                    day_tolerance=args.day_tolerance,
                )
            except Exception as e:
                logger.warning("excel_match_error\t%s\t%s", path, repr(e))
                excel_row = None

            if not excel_row:
                logger.info(
                    "excel_no_match\t%s\tPatientID=%s\tAcc=%s\tStudyDT=%s",
                    path,
                    meta.patient_id,
                    meta.accession_number,
                    meta.study_datetime,
                )
                continue

            total_excel_matched += 1

            # 3) 读像素并导出 PNG（需要重新读取像素，避免前面 stop_before_pixels）
            try:
                tmp_dir = tmp_root / f"tmp_{uuid.uuid4().hex}"
                ds_pix = read_dicom(path, stop_before_pixels=False)
                written = export_png(ds_pix, tmp_dir, base_name="image")
                if not written:
                    raise RuntimeError("no_png_written")
                total_png_ok += 1
            except Exception as e:
                logger.warning("png_export_fail\t%s\t%s", path, repr(e))
                try:
                    if 'tmp_dir' in locals() and tmp_dir.exists():
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
                continue

            # 4) 完全成功后才分配 idx：移动到 idx 目录 + 写 jsonl 均成功，才递增
            idx = f"{month}-{next_n:05d}"
            final_dir = image_root / idx
            try:
                # 若存在同名目录（通常是重复跑/中断导致），先报错避免覆盖
                if final_dir.exists():
                    raise FileExistsError(f"target_exists: {final_dir}")

                shutil.move(str(tmp_dir), str(final_dir))

                rel_image_path = os.path.relpath(final_dir, root).replace("\\", "/")
                dicom_meta_dict = asdict(meta)
                dicom_meta_dict["source_dicom"] = os.path.relpath(path, root).replace("\\", "/")

                rec = ordered_record(
                    idx=idx,
                    image_path=rel_image_path,
                    excel_row=excel_row,
                    dicom_meta=dicom_meta_dict,
                )
                jf.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
                jf.flush()

                total_written += 1
                next_n += 1
            except Exception as e:
                logger.warning("finalize_fail\t%s\tidx=%s\t%s", path, idx, repr(e))
                # 回滚：删除已经移动过去的目录；或删除临时目录
                try:
                    if final_dir.exists():
                        shutil.rmtree(final_dir, ignore_errors=True)
                    elif tmp_dir.exists():
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
                continue

    denom = max(len(to_process), 1)
    ratio = (total_written / denom)
    logger.info("summary probable_dicoms=%d", len(candidates))
    logger.info("summary processed=%d", len(to_process))
    logger.info("summary dicom_read_ok=%d", total_dicom_read_ok)
    logger.info("summary excel_matched=%d", total_excel_matched)
    logger.info("summary png_ok=%d", total_png_ok)
    logger.info("summary written=%d", total_written)
    logger.info("summary pass_ratio=%.4f", ratio)
    logger.info("summary last_idx=%s", f"{month}-{(next_n-1):05d}" if total_written else "(none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
