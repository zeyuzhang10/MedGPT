from __future__ import annotations

import re


_ws_re = re.compile(r"\s+")
_non_alnum_re = re.compile(r"[^0-9a-zA-Z\u4e00-\u9fff]+")


def norm_text(value: str | None) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    s = _ws_re.sub("", s)
    s = _non_alnum_re.sub("", s)
    return s.upper()


def norm_digits(value: str | None) -> str:
    if value is None:
        return ""
    s = re.sub(r"\D+", "", str(value))
    return s
