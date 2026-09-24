"""A zero-height Streamlit component that reports its content-column width."""

from pathlib import Path

import streamlit.components.v1 as components

_COMPONENT_PATH = Path(__file__).with_name("content_width_component")
_content_width_component = components.declare_component(
    "perimeter_content_width_v3",
    path=str(_COMPONENT_PATH),
)


def get_content_width(default: int = 630, key: str = "content_width") -> int:
    value = _content_width_component(default=default, key=key)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default
