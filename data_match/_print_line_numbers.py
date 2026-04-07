from __future__ import annotations

from pathlib import Path


def main() -> None:
    p = Path(r"F:\dicom_dataset_tools\dicom_pipeline\dicom_utils.py")
    lines = p.read_text(encoding="utf-8").splitlines()
    for i, l in enumerate(lines, 1):
        if l.startswith("def parse_study_datetime") or l.startswith("def extract_meta"):
            print(i, l.strip())


if __name__ == "__main__":
    main()
