"""Translation Lens for macOS."""

from . import theme
from .lens import draw_axolotl, main, set_theme

# Live palette names must resolve through theme (set_theme mutates them).
_LIVE = frozenset(theme.PALETTE_NAMES)


def __getattr__(name):
    if name in _LIVE or hasattr(theme, name):
        return getattr(theme, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "C_BORDER",
    "C_HEADER",
    "C_PANEL",
    "draw_axolotl",
    "main",
    "set_theme",
]
