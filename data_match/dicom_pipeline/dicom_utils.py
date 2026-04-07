from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DicomMeta:
    patient_id: str | None
    accession_number: str | None
    study_instance_uid: str | None
    series_instance_uid: str | None
    sop_instance_uid: str | None
    study_datetime: datetime | None
    modality: str | None
    manufacturer_model: str | None


def _read_preamble_has_dicm(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            head = f.read(132)
        return len(head) >= 132 and head[128:132] == b"DICM"
    except Exception:
        return False


def is_probably_dicom(path: Path, aggressive: bool = False) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".dcm", ".dicom", ".ima"}:
        return True
    if _read_preamble_has_dicm(path):
        return True
    if aggressive and suffix in {"", ".dat", ".bin"}:
        return True
    return False


def read_dicom(path: Path, *, stop_before_pixels: bool = False):
    import pydicom

    # force=True: 允许部分无 preamble 的 DICOM
    return pydicom.dcmread(
        str(path),
        stop_before_pixels=stop_before_pixels,
        force=True,
        specific_tags=None,
    )


def _get_first(ds: Any, keys: list[str]) -> str | None:
    for k in keys:
        try:
            v = getattr(ds, k, None)
        except Exception:
            v = None
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def parse_study_datetime(ds: Any) -> datetime | None:
    # 有些设备直接给组合字段 AcquisitionDateTime
    adt = _get_first(ds, ["AcquisitionDateTime"])
    if adt:
        s = str(adt).strip()
        # 20240401101501.238103 -> 取到秒
        s_main = s.split(".", 1)[0]
        try:
            if len(s_main) >= 14:
                return datetime.strptime(s_main[:14], "%Y%m%d%H%M%S")
        except Exception:
            pass

    # 常见组合：StudyDate(YYYYMMDD) + StudyTime(HHMMSS.frac)
    date_str = _get_first(ds, ["StudyDate", "AcquisitionDate", "ContentDate", "SeriesDate"])
    time_str = _get_first(ds, ["StudyTime", "AcquisitionTime", "ContentTime", "SeriesTime"])

    if not date_str:
        return None

    date_str = str(date_str)
    time_str = str(time_str or "")

    # 标准化 time: 只取数字和小数点
    time_str = "".join(ch for ch in time_str if ch.isdigit() or ch == ".")

    try:
        if time_str:
            # HHMMSS[.ffffff]
            if "." in time_str:
                main, frac = time_str.split(".", 1)
            else:
                main, frac = time_str, ""
            main = (main + "000000")[:6]
            fmt = "%Y%m%d%H%M%S"
            dt = datetime.strptime(date_str + main, fmt)
            return dt
        return datetime.strptime(date_str, "%Y%m%d")
    except Exception:
        return None


def extract_meta(ds: Any) -> DicomMeta:
    patient_id = _get_first(ds, ["PatientID", "OtherPatientIDs", "PatientName"])

    # 放射编号在不同机构命名不同：AccessionNumber 最常见
    accession_number = _get_first(
        ds,
        [
            "AccessionNumber",
            "StudyID",
            "RequestedProcedureID",
            "ScheduledProcedureStepID",
            "OtherStudyNumbers",
        ],
    )

    study_instance_uid = _get_first(ds, ["StudyInstanceUID"])
    series_instance_uid = _get_first(ds, ["SeriesInstanceUID"])
    sop_instance_uid = _get_first(ds, ["SOPInstanceUID"])
    modality = _get_first(ds, ["Modality"])
    manufacturer_model = _get_first(ds, ["ManufacturerModelName", "Manufacturer"])

    study_dt = parse_study_datetime(ds)

    return DicomMeta(
        patient_id=patient_id,
        accession_number=accession_number,
        study_instance_uid=study_instance_uid,
        series_instance_uid=series_instance_uid,
        sop_instance_uid=sop_instance_uid,
        study_datetime=study_dt,
        modality=modality,
        manufacturer_model=manufacturer_model,
    )


def export_png(ds: Any, out_dir: Path, *, base_name: str = "image") -> list[Path]:
    """Export PNG(s) to out_dir. Returns list of written paths.

    - 单帧：写 1 张
    - 多帧：写 N 张（image_000.png ...）

    若像素无法解码/缺失会抛异常。
    """

    import numpy as np
    from PIL import Image
    from pydicom.pixel_data_handlers.util import apply_voi_lut

    out_dir.mkdir(parents=True, exist_ok=True)

    arr = ds.pixel_array  # may raise

    # VOI LUT（对部分 CT/CR 更友好）
    try:
        arr = apply_voi_lut(arr, ds)
    except Exception:
        pass

    # 多帧：shape (frames, H, W) 或 (frames, H, W, C)
    written: list[Path] = []

    def _to_uint8(img: np.ndarray) -> np.ndarray:
        img = img.astype(np.float32)
        if img.ndim == 3 and img.shape[-1] in (3, 4):
            # 已是 RGB/RGBA
            return img.astype(np.uint8)
        vmin = float(np.nanmin(img))
        vmax = float(np.nanmax(img))
        if vmax <= vmin:
            return np.zeros_like(img, dtype=np.uint8)
        img = (img - vmin) / (vmax - vmin)
        img = np.clip(img * 255.0, 0, 255)
        return img.astype(np.uint8)

    def _save_one(img: np.ndarray, path: Path) -> None:
        img8 = _to_uint8(img)
        if img8.ndim == 2:
            im = Image.fromarray(img8, mode="L")
        elif img8.ndim == 3 and img8.shape[-1] == 3:
            im = Image.fromarray(img8, mode="RGB")
        elif img8.ndim == 3 and img8.shape[-1] == 4:
            im = Image.fromarray(img8, mode="RGBA")
        else:
            # 兜底：尝试压成 2D
            im = Image.fromarray(img8.squeeze(), mode="L")
        im.save(str(path), format="PNG")

    if arr.ndim >= 3 and (getattr(ds, "NumberOfFrames", None) or 0) not in (None, 0, 1):
        frames = arr.shape[0]
        for i in range(frames):
            path = out_dir / f"{base_name}_{i:03d}.png"
            _save_one(arr[i], path)
            written.append(path)
        return written

    path = out_dir / f"{base_name}.png"
    _save_one(arr, path)
    written.append(path)
    return written


def safe_filesize(path: Path) -> int:
    try:
        return path.stat().st_size
    except Exception:
        return -1


def is_too_large(path: Path, max_mb: int) -> bool:
    size = safe_filesize(path)
    if size < 0:
        return False
    return size > max_mb * 1024 * 1024
