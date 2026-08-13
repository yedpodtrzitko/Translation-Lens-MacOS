"""Accent-derived UI palette and layout geometry."""

from AppKit import NSColor


def rgb(r, g, b, a=1.0):
    return NSColor.colorWithSRGBRed_green_blue_alpha_(
        r / 255.0, g / 255.0, b / 255.0, a
    )


#: Every surface color is derived from one accent hue, so a theme change
#: stays coherent.  Brightness is kept high across all themes: the tone
#: colors below are a fixed learning convention and must stay legible on the
#: panel whatever accent is chosen.
THEMES = (
    ("Sakura", 340, 1.00),
    ("Peach", 18, 1.00),
    ("Amber", 42, 0.95),
    ("Matcha", 105, 0.85),
    ("Mint", 165, 0.85),
    ("Sky", 205, 0.90),
    ("Lavender", 278, 0.85),
    ("Slate", 222, 0.35),
)
DEFAULT_HUE, DEFAULT_SAT = 340, 1.00

PALETTE_NAMES = (
    "C_HEADER",
    "C_HEADER_2",
    "C_PANEL",
    "C_BORDER",
    "C_TINT",
    "C_DEEP",
    "C_INK",
    "C_INK_SOFT",
    "C_TITLE",
    "C_TITLE_SUB",
    "C_AXO_BODY",
    "C_AXO_GILL",
    "C_AXO_LINE",
    "C_AXO_BLUSH",
    "THEME_HUE",
    "THEME_SAT",
)

_change_hooks = []


def on_change(callback):
    """Run `callback` after every successful `set_theme` (e.g. clear tint caches)."""
    _change_hooks.append(callback)


def set_theme(hue, sat=1.0):
    """Recompute the palette from an accent hue (degrees) and saturation."""
    global C_HEADER, C_HEADER_2, C_PANEL, C_BORDER, C_TINT, C_DEEP
    global C_INK, C_INK_SOFT, C_TITLE, C_TITLE_SUB
    global C_AXO_BODY, C_AXO_GILL, C_AXO_LINE, C_AXO_BLUSH, THEME_HUE, THEME_SAT

    def hsb(h, s, b, a=1.0):
        return NSColor.colorWithHue_saturation_brightness_alpha_(
            (h % 360) / 360.0, max(0.0, min(1.0, s * sat)), b, a
        )

    THEME_HUE, THEME_SAT = hue, sat
    C_HEADER = hsb(hue, 0.33, 1.00)
    C_HEADER_2 = hsb(hue, 0.23, 1.00)
    C_PANEL = hsb(hue, 0.05, 0.92)
    C_BORDER = hsb(hue, 0.57, 0.94)
    C_TINT = hsb(hue, 0.40, 1.00, 0.07)
    C_DEEP = hsb(hue, 0.68, 0.75)
    C_INK = hsb(hue, 0.30, 0.24)
    C_INK_SOFT = hsb(hue, 0.20, 0.47)
    C_TITLE = hsb(hue, 0.75, 0.55)
    C_TITLE_SUB = hsb(hue, 0.55, 0.62, 0.85)
    C_AXO_BODY = hsb(hue, 0.14, 1.00)
    C_AXO_GILL = hsb(hue, 0.42, 1.00)
    C_AXO_LINE = hsb(hue, 0.65, 0.84)
    C_AXO_BLUSH = hsb(hue, 0.48, 1.00, 0.75)
    for hook in _change_hooks:
        hook()


def theme_swatch(hue, sat, kind="fill"):
    """A theme's representative color, without touching the live palette."""

    def hsb(sa, b, a=1.0):
        return NSColor.colorWithHue_saturation_brightness_alpha_(
            (hue % 360) / 360.0, max(0.0, min(1.0, sa * sat)), b, a
        )

    if kind == "edge":
        return hsb(0.70, 0.78)
    return hsb(0.50, 1.00)


def sync_palette(namespace):
    """Copy live palette names into another module's globals (keeps bare `C_*` live)."""
    g = globals()
    for name in PALETTE_NAMES:
        namespace[name] = g[name]


set_theme(DEFAULT_HUE, DEFAULT_SAT)

# Tone colors: 1 red, 2 amber, 3 green, 4 blue, 5/neutral gray.
TONE_COLORS = {
    1: rgb(224, 41, 92),
    2: rgb(212, 124, 0),
    3: rgb(24, 150, 78),
    4: rgb(56, 105, 214),
    5: rgb(140, 140, 153),
}

HEADER_H = 34
RESULTS_H = 264
CORNER = 14

# The reading frame is sized independently of the window: the window has to
# stay wide enough to read definitions in, but the frame needs to shrink to a
# couple of characters.  So the frame is an inset rect inside a transparent
# band, anchored at the window's top-left.
WIN_W_MIN = 380
FRAME_INSET = 12
FRAME_PAD = 6
FRAME_W_DEFAULT = 300
FRAME_H_DEFAULT = 76
FRAME_W_MIN = 44
FRAME_H_MIN = 26
FRAME_W_MAX = 1100
FRAME_H_MAX = 600

#: quick sizes, roughly: one character, a word, a line, a whole bubble
PRESETS = (
    ("Character", 56, 52),
    ("Word", 116, 56),
    ("Line", 300, 60),
    ("Bubble", 360, 130),
)
