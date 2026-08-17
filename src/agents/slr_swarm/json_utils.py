"""Đọc JSON từ output LLM một cách chịu lỗi.

Model local (kể cả khi đã Grammar-Constrained Decoding) vẫn có lúc kèm ```json fence
hoặc câu dẫn. Ta bóc phần JSON đầu tiên thay vì để cả pipeline vỡ.
"""

from __future__ import annotations

import json
from typing import Any

_OPEN = {"{": "}", "[": "]"}


def extract_json(text: str) -> Any | None:
    """Bóc object/array JSON cân bằng ngoặc đầu tiên trong `text`."""
    if not text:
        return None

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    for index, char in enumerate(text):
        closing = _OPEN.get(char)
        if closing is None:
            continue
        depth = 0
        in_string = False
        escaped = False
        for cursor in range(index, len(text)):
            current = text[cursor]
            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == char:
                depth += 1
            elif current == closing:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[index : cursor + 1])
                    except json.JSONDecodeError:
                        break
    return None


def parse_object(text: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    parsed = extract_json(text)
    if isinstance(parsed, dict):
        return parsed
    return dict(default or {})


def as_str_list(value: Any) -> list[str]:
    """Ép về list[str]; LLM hay trả string đơn hoặc list lẫn kiểu."""
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]
