"""Screen capture, preprocessing and Vision OCR for the reading lens."""

import re

import Quartz
import Vision
from AppKit import NSScreen

from . import langs

CJK_RE = langs.CJK_RE


def capture_below_window(win_number, screen_rect):
    """Grab the pixels under `screen_rect`, excluding our own window."""
    primary_h = NSScreen.screens()[0].frame().size.height
    cg = Quartz.CGRectMake(
        screen_rect.origin.x,
        primary_h - (screen_rect.origin.y + screen_rect.size.height),
        screen_rect.size.width,
        screen_rect.size.height,
    )
    return Quartz.CGWindowListCreateImage(
        cg,
        Quartz.kCGWindowListOptionOnScreenBelowWindow,
        win_number,
        Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageBestResolution,
    )


def upscale(cgimg, factor):
    if factor <= 1.001:
        return cgimg
    w = Quartz.CGImageGetWidth(cgimg)
    h = Quartz.CGImageGetHeight(cgimg)
    nw, nh = int(w * factor), int(h * factor)
    cs = Quartz.CGColorSpaceCreateDeviceRGB()
    ctx = Quartz.CGBitmapContextCreate(
        None,
        nw,
        nh,
        8,
        0,
        cs,
        Quartz.kCGImageAlphaPremultipliedFirst | Quartz.kCGBitmapByteOrder32Little,
    )
    if ctx is None:
        return cgimg
    Quartz.CGContextSetInterpolationQuality(ctx, Quartz.kCGInterpolationHigh)
    Quartz.CGContextDrawImage(ctx, Quartz.CGRectMake(0, 0, nw, nh), cgimg)
    return Quartz.CGBitmapContextCreateImage(ctx)


def _gray_pixels(cgimg):
    """-> (bytearray of row-major uint8, width, height), or None.

    Row 0 is the top of the image.  Kept as a tight bytearray (no row stride)
    so the vertical-reflow ink mask stays small without a numeric array library.
    """
    w = Quartz.CGImageGetWidth(cgimg)
    h = Quartz.CGImageGetHeight(cgimg)
    ctx = Quartz.CGBitmapContextCreate(
        None,
        w,
        h,
        8,
        0,
        Quartz.CGColorSpaceCreateDeviceGray(),
        Quartz.kCGImageAlphaNone,
    )
    if ctx is None:
        return None
    Quartz.CGContextDrawImage(ctx, Quartz.CGRectMake(0, 0, w, h), cgimg)
    stride = Quartz.CGBitmapContextGetBytesPerRow(ctx)
    raw = Quartz.CGBitmapContextGetData(ctx).as_buffer(stride * h)
    if stride == w:
        return bytearray(raw), w, h
    out = bytearray(w * h)
    for y in range(h):
        start = y * stride
        out[y * w : (y + 1) * w] = raw[start : start + w]
    return out, w, h


def _median_u8(samples):
    if not samples:
        return 0
    s = sorted(samples)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) // 2


def _runs(flags, gap):
    """Index ranges of consecutive True values, bridging gaps up to `gap`."""
    out = []
    start = None
    for i, on in enumerate(flags):
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append([start, i])
            start = None
    if start is not None:
        out.append([start, len(flags)])
    merged = []
    for r in out:
        if merged and r[0] - merged[-1][1] <= gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged


def reflow_vertical(cgimg, max_cells=64):
    """Turn a vertical-text image into a horizontal strip Vision can read.

    Vision's Chinese recognizer only handles horizontal lines — a column of
    stacked characters yields zero observations — but it reads isolated
    characters perfectly.  So slice the columns into character cells and
    paste them side by side in reading order (rightmost column first), which
    also keeps enough context for language correction to help.
    """
    got = _gray_pixels(cgimg)
    if got is None:
        return None
    gray, w, h = got
    if w < 12 or h < 12:
        return None

    border = []
    border.extend(gray[:w])  # top
    border.extend(gray[(h - 1) * w : h * w])  # bottom
    border.extend(gray[y * w] for y in range(h))  # left
    border.extend(gray[y * w + (w - 1)] for y in range(h))  # right
    bg = _median_u8(border)

    ink = bytearray(w * h)
    any_ink = False
    for i, px in enumerate(gray):
        if abs(px - bg) > 60:
            ink[i] = 1
            any_ink = True
    if not any_ink:
        return None

    col_ink = [False] * w
    for y in range(h):
        base = y * w
        for x in range(w):
            if ink[base + x]:
                col_ink[x] = True

    cols = _runs(col_ink, gap=1)
    if not cols:
        return None
    # Characters are square, so the widest raw band approximates one glyph;
    # use it to bridge the white gaps inside characters like 川.
    glyph = max(c[1] - c[0] for c in cols)
    cols = _runs(col_ink, gap=max(1, int(glyph * 0.4)))
    cols = [c for c in cols if (c[1] - c[0]) >= glyph * 0.5]
    if not cols:
        return None

    cells = []
    for x0, x1 in sorted(cols, key=lambda c: -c[0]):  # right to left
        cw = x1 - x0
        row_ink = [False] * h
        for y in range(h):
            base = y * w
            for x in range(x0, x1):
                if ink[base + x]:
                    row_ink[y] = True
                    break
        rows = _runs(row_ink, gap=1)
        group = None
        for y0, y1 in rows:
            if group is not None and (y1 - group[0]) <= cw * 1.25:
                group[1] = y1
            else:
                if group is not None:
                    cells.append((x0, group[0], cw, group[1] - group[0]))
                group = [y0, y1]
        if group is not None:
            cells.append((x0, group[0], cw, group[1] - group[0]))
    if not 2 <= len(cells) <= max_cells:
        return None

    pad = max(4, glyph // 6)
    strip_h = max(c[3] for c in cells) + 2 * pad
    strip_w = sum(c[2] for c in cells) + pad * (len(cells) + 1)
    ctx = Quartz.CGBitmapContextCreate(
        None,
        strip_w,
        strip_h,
        8,
        0,
        Quartz.CGColorSpaceCreateDeviceRGB(),
        Quartz.kCGImageAlphaPremultipliedFirst | Quartz.kCGBitmapByteOrder32Little,
    )
    if ctx is None:
        return None
    Quartz.CGContextSetRGBFillColor(ctx, 1, 1, 1, 1)
    Quartz.CGContextFillRect(ctx, Quartz.CGRectMake(0, 0, strip_w, strip_h))
    x = pad
    for cx, cy, cw, ch in cells:
        piece = Quartz.CGImageCreateWithImageInRect(
            cgimg, Quartz.CGRectMake(cx, cy, cw, ch)
        )
        Quartz.CGContextDrawImage(
            ctx, Quartz.CGRectMake(x, (strip_h - ch) / 2.0, cw, ch), piece
        )
        x += cw + pad
    return Quartz.CGBitmapContextCreateImage(ctx)


def denoise(text):
    """Drop stray single latin letters.

    A tight frame clips the glyphs either side of the one you're aiming at,
    and Vision reads those slivers as lone roman letters ("E說").  They never
    reach the dictionary — segmentation keeps only the target script — but
    they make the "read" line look wrong.  Only ever applied to CJK/Hangul
    languages, where a lone roman letter is always noise.
    """
    if not text:
        return text
    return re.sub(r"(?<![0-9A-Za-z])[A-Za-z](?![0-9A-Za-z])", "", text).strip()


def ocr_text(cgimg, lang):
    """Return recognized text, ordered for horizontal or vertical layouts."""
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(0)  # accurate
    req.setRecognitionLanguages_(list(lang.ocr_langs))
    req.setUsesLanguageCorrection_(True)
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cgimg, {})
    ok, err = handler.performRequests_error_([req], None)
    if not ok:
        return ""
    obs = req.results() or []
    items = []
    for o in obs:
        cands = o.topCandidates_(1)
        if not cands or len(cands) == 0:
            continue
        bb = o.boundingBox()
        items.append((bb, cands[0].string()))
    if not items:
        return ""
    tall = sum(1 for bb, _ in items if bb.size.height > bb.size.width * 1.3)
    if lang.vertical_ok and tall > len(items) / 2.0:
        # vertical CJK: columns run right to left
        items.sort(key=lambda it: -it[0].origin.x)
    else:
        # Bucket into lines by text height before sorting left-to-right, so two
        # fragments of the same line don't swap just because one sits a pixel
        # higher than the other.
        heights = sorted(bb.size.height for bb, _ in items)
        band = max(heights[len(heights) // 2], 0.01)
        items.sort(key=lambda it: (-int(it[0].origin.y / band), it[0].origin.x))
    text = "".join(t for _, t in items)
    return denoise(text) if lang.strip_stray_latin else text


def recognize_under_window(win_number, screen_rect, lang):
    """Capture under the lens and OCR it.

    Returns the recognized string (possibly empty), or ``None`` if the
    capture itself failed (typically a Screen Recording permission issue).
    """
    img = capture_below_window(win_number, screen_rect)
    if img is None:
        return None
    h = Quartz.CGImageGetHeight(img)
    factor = 1.0
    if h < 300:
        factor = min(4.0, max(1.0, 300.0 / max(h, 1)))
    big = upscale(img, factor)
    text = ocr_text(big, lang)
    if lang.vertical_ok and len(CJK_RE.findall(text)) < 2:
        # probably a vertical speech bubble
        strip = reflow_vertical(big)
        if strip is not None:
            alt = ocr_text(strip, lang)
            if len(CJK_RE.findall(alt)) > len(CJK_RE.findall(text)):
                text = alt
    return text
