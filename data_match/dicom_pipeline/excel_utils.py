from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .similarity import similarity_ratio
from .text_norm import norm_digits, norm_text


@dataclass
class ExcelIndex:
    df: pd.DataFrame
    patient_col: str
    accession_col: str
    time_col: str


def _best_header_match(headers: list[str], candidates: list[str], *, threshold: float) -> str | None:
    best_col = None
    best_score = 0.0
    for h in headers:
        hn = norm_text(h)
        for c in candidates:
            score = similarity_ratio(hn, norm_text(c))
            if score > best_score:
                best_score = score
                best_col = h
    if best_col is None:
        return None
    return best_col if best_score >= threshold else None


def infer_key_columns(df: pd.DataFrame) -> tuple[str, str, str]:
    headers = [str(c) for c in df.columns]

    # 表头候选：你可以按你的真实 Excel 表头再加词
    patient_candidates = [
        "病人编号",
        "患者编号",
        "病人ID",
        "患者ID",
        "PatientID",
        "PID",
    ]

    accession_candidates = [
        "放射编号",
        "放射号",
        "检查号",
        "检查编号",
        "影像编号",
        "影像号",
        "AccessionNumber",
        "Accession",
        "StudyID",
    ]

    time_candidates = [
        "检查时间",
        "检查日期",
        "检查日期时间",
        "检查时间点",
        "StudyDate",
        "ExamTime",
        "Time",
    ]

    # 阈值略低一些，避免表头稍微不同就找不到
    patient_col = _best_header_match(headers, patient_candidates, threshold=0.75) or headers[0]
    accession_col = _best_header_match(headers, accession_candidates, threshold=0.75) or headers[min(1, len(headers) - 1)]
    time_col = _best_header_match(headers, time_candidates, threshold=0.75) or headers[min(2, len(headers) - 1)]

    return patient_col, accession_col, time_col


def load_excel(excel_path: Path) -> pd.DataFrame:
    # dtype=str 避免编号被当成科学计数法/丢前导0
    df = pd.read_excel(str(excel_path), dtype=str, engine="openpyxl")
    df = df.fillna("")
    return df


def build_index(excel_path: Path) -> ExcelIndex:
    df = load_excel(excel_path)
    patient_col, accession_col, time_col = infer_key_columns(df)

    df["__pid_norm"] = df[patient_col].map(norm_text)
    df["__acc_norm"] = df[accession_col].map(norm_text)

    # 解析时间：尽量容错
    dt = pd.to_datetime(df[time_col], errors="coerce")
    df["__dt"] = dt
    df["__date_norm"] = dt.dt.strftime("%Y%m%d").fillna("")

    return ExcelIndex(df=df, patient_col=patient_col, accession_col=accession_col, time_col=time_col)


def _date_norm_from_dt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y%m%d")


def match_row(
    index: ExcelIndex,
    *,
    patient_id: str | None,
    accession_number: str | None,
    study_dt: datetime | None,
    fuzz_threshold: float = 0.90,
    day_tolerance: int = 1,
) -> dict[str, Any] | None:
    """在 Excel 里匹配一行，返回该行 dict（不含内部列）或 None。

    匹配策略：
    1) pid+acc 精确（规范化后）命中优先
    2) 加上日期一致（或在 day_tolerance 内）加分
    3) 兜底用相似度（rapidfuzz/difflib）
    """

    df = index.df

    pid = norm_text(patient_id)
    acc = norm_text(accession_number)
    date_norm = _date_norm_from_dt(study_dt)

    if pid and acc:
        exact = df[(df["__pid_norm"] == pid) & (df["__acc_norm"] == acc)]
        if len(exact) == 1:
            row = exact.iloc[0].to_dict()
            return {k: v for k, v in row.items() if not k.startswith("__")}
        if len(exact) > 1:
            # 多条：优先日期最接近
            if date_norm:
                exact2 = exact.copy()
                exact2["__date_score"] = (exact2["__date_norm"] == date_norm).astype(int)
                exact2 = exact2.sort_values(["__date_score"], ascending=False)
                row = exact2.iloc[0].to_dict()
                return {k: v for k, v in row.items() if not k.startswith("__")}
            row = exact.iloc[0].to_dict()
            return {k: v for k, v in row.items() if not k.startswith("__")}

    # 缩小候选：有 pid 就先用 pid 过滤；否则有 acc 用 acc 过滤；否则全表（可能慢）
    cand = df
    if pid:
        cand = df[df["__pid_norm"] == pid]
    elif acc:
        cand = df[df["__acc_norm"] == acc]

    if len(cand) == 0:
        cand = df

    best = None
    best_score = -1.0

    for _, r in cand.iterrows():
        s_pid = similarity_ratio(pid, r["__pid_norm"]) if pid else 0.0
        s_acc = similarity_ratio(acc, r["__acc_norm"]) if acc else 0.0
        s_date = 0.0
        if date_norm and r["__date_norm"]:
            if r["__date_norm"] == date_norm:
                s_date = 1.0
            else:
                # 容忍天级偏差：用日期字符串粗略比较（不做重计算也行）
                try:
                    dt_r = r["__dt"]
                    if pd.isna(dt_r):
                        dt_r = None
                except Exception:
                    dt_r = None
                if dt_r is not None and study_dt is not None:
                    delta_days = abs((study_dt.date() - dt_r.date()).days)
                    if delta_days <= day_tolerance:
                        s_date = 0.8

        # 加权：pid/acc 关键更大
        score = 0.45 * s_pid + 0.45 * s_acc + 0.10 * s_date
        if score > best_score:
            best_score = score
            best = r

    # 要求 pid/acc 至少有一个足够像，并且总体达到阈值
    if best is None:
        return None

    pid_ok = (not pid) or similarity_ratio(pid, best["__pid_norm"]) >= fuzz_threshold
    acc_ok = (not acc) or similarity_ratio(acc, best["__acc_norm"]) >= fuzz_threshold

    if (pid and acc and pid_ok and acc_ok) or (pid_ok and acc_ok and best_score >= fuzz_threshold * 0.8):
        row = best.to_dict()
        return {k: v for k, v in row.items() if not k.startswith("__")}

    return None
