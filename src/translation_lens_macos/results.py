"""Attributed strings for the results panel: dictionary hits, welcome, credits."""

from typing import TYPE_CHECKING, Literal

from Foundation import NSMakeRect, NSMutableAttributedString, NSAttributedString
from AppKit import (
    NSColor,
    NSFont,
    NSImage,
    NSTextAttachment,
    NSCursor,
    NSImageSymbolConfiguration,
    NSCompositingOperationSourceAtop,
    NSCompositingOperationSourceOver,
    NSRectFillUsingOperation,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSParagraphStyleAttributeName,
    NSMutableParagraphStyle,
    NSLineBreakByWordWrapping,
    NSCursorAttributeName,
    NSLinkAttributeName,
)

from . import theme
from .theme import TONE_COLORS

if TYPE_CHECKING:
    from .langs import Language

_tinted_icons: dict[
    tuple[str, float], NSImage | None
] = {}  # tinted glyphs, cleared whenever the theme changes
theme.on_change(_tinted_icons.clear)


# ---------------------------------------------------------------- fonts ---


def rounded_font(size: float, bold: bool = False) -> NSFont:
    weight = 0.4 if bold else 0.0
    base = NSFont.systemFontOfSize_weight_(size, weight)
    try:
        desc = base.fontDescriptor().fontDescriptorWithDesign_(
            "NSCTFontUIFontDesignRounded"
        )
        if desc is not None:
            f = NSFont.fontWithDescriptor_size_(desc, size)
            if f is not None:
                return f
    except Exception:
        pass
    return base


def attr(
    text: str,
    font: NSFont,
    color: NSColor,
    para: NSMutableParagraphStyle | None = None,
) -> NSAttributedString:
    d = {NSFontAttributeName: font, NSForegroundColorAttributeName: color}
    if para is not None:
        d[NSParagraphStyleAttributeName] = para
    return NSAttributedString.alloc().initWithString_attributes_(text, d)


def make_para(
    head: float = 0.0,
    before: float = 0.0,
    after: float = 0.0,
    lead: float = 2.0,
) -> NSMutableParagraphStyle:
    p = NSMutableParagraphStyle.alloc().init()
    p.setHeadIndent_(head)
    p.setFirstLineHeadIndent_(0.0)
    p.setParagraphSpacingBefore_(before)
    p.setParagraphSpacing_(after)
    p.setLineSpacing_(lead)
    p.setLineBreakMode_(NSLineBreakByWordWrapping)
    return p


def word_font(lang: Language, size: float) -> NSFont:
    if lang.font_name:
        f = NSFont.fontWithName_size_(lang.font_name, size)
        if f is not None:
            return f
    return rounded_font(size, True)


# ---------------------------------------------------------- inline icons ---


def tinted_symbol(name: str, accessibility: str, size: float) -> NSImage | None:
    """A small pink SF Symbol glyph for inline use in the results panel."""
    key = (name, size)
    if key in _tinted_icons:
        return _tinted_icons[key]
    img: NSImage | None = None
    try:
        base = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            name, accessibility
        )
        if base is not None:
            cfg = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                size, 0, 2
            )
            base = base.imageWithSymbolConfiguration_(cfg)
            r = NSMakeRect(0, 0, base.size().width, base.size().height)
            img = NSImage.alloc().initWithSize_(base.size())
            img.lockFocus()
            base.drawInRect_fromRect_operation_fraction_(
                r, NSMakeRect(0, 0, 0, 0), NSCompositingOperationSourceOver, 1.0
            )
            theme.C_DEEP.set()
            NSRectFillUsingOperation(r, NSCompositingOperationSourceAtop)
            img.unlockFocus()
    except Exception:
        img = None
    _tinted_icons[key] = img
    return img


def _icon_link(
    url: str, img: NSImage | None, fallback: str
) -> NSMutableAttributedString:
    if img is None:
        piece = NSMutableAttributedString.alloc().initWithString_(fallback)
    else:
        att = NSTextAttachment.alloc().init()
        att.setImage_(img)
        piece = NSMutableAttributedString.alloc().initWithAttributedString_(
            NSAttributedString.attributedStringWithAttachment_(att)
        )
    piece.addAttributes_range_(
        {
            NSLinkAttributeName: url,
            NSCursorAttributeName: NSCursor.pointingHandCursor(),
        },
        (0, piece.length()),
    )
    return piece


def speaker_icon(size: float = 16.0) -> NSImage | None:
    return tinted_symbol("speaker.wave.2.fill", "speak", size)


def speak_link(index: int, size: float = 16.0) -> NSMutableAttributedString:
    """Clickable speaker icon; the link carries an index into `speakables`."""
    return _icon_link("speak:%d" % index, speaker_icon(size), "♪")


def copy_link(size: float = 16.0) -> NSMutableAttributedString:
    """Clickable copy icon; copies the detected text to the clipboard."""
    return _icon_link("copy:", tinted_symbol("doc.on.doc", "copy", size), "⎘")


# --------------------------------------------------------------- credits ---

#: Shown by Help -> Licenses & Credits.  The dictionaries are all share-alike
#: licensed, which obliges any distributed build to carry this attribution.
CREDITS: list[tuple[str, str]] = [
    (
        "Translation Lens",
        "Reading lens for Chinese, Japanese, Korean, French, "
        "Spanish, Italian and German.",
    ),
    (
        "Dictionary data — CC BY-SA 4.0",
        "Chinese: CC-CEDICT (mdbg.net).\n"
        "Japanese: JMdict/EDICT, Electronic Dictionary Research and Development "
        "Group (edrdg.org).\n"
        "Korean: English Wiktionary, extracted by kaikki.org.\n"
        "French, Spanish, Italian, German: WikDict (wikdict.com), from "
        "Wiktionary.\n\n"
        "These dictionaries are licensed CC BY-SA 4.0. The lexicon files shipped "
        "with this app are adaptations of them and remain under the same license; "
        "they are available on request.",
    ),
    (
        "Software libraries",
        "jieba (MIT) — Chinese word segmentation.\n"
        "pypinyin (MIT) — pinyin readings.\n"
        "simplemma (MIT) — lemmatisation.\n"
        "PyObjC (MIT), NumPy (BSD), Python (PSF).",
    ),
    (
        "System frameworks",
        "Text recognition uses Apple's Vision framework; speech uses "
        "AVSpeechSynthesizer. Both run on-device — no text leaves your Mac.",
    ),
]


def credits_text() -> NSMutableAttributedString:
    s = NSMutableAttributedString.alloc().init()
    for title, body in CREDITS:
        s.appendAttributedString_(
            attr(
                title + "\n",
                rounded_font(13, True),
                theme.C_DEEP,
                make_para(before=8, after=3),
            )
        )
        s.appendAttributedString_(
            attr(
                body + "\n",
                rounded_font(11),
                theme.C_INK_SOFT,
                make_para(lead=2.5, after=4),
            )
        )
    return s


# ---------------------------------------------------------- results text ---


def build_results(
    raw_text: str, lang: Language
) -> tuple[NSMutableAttributedString, list[tuple[str, str]]]:
    """-> (attributed string, speakables)

    `speakables` is what the speaker icons point at: index -> (text, voice).
    """
    out = NSMutableAttributedString.alloc().init()
    speakables: list[tuple[str, str]] = []

    said: set[tuple[int | None, str]] = set()

    def add_speaker(text: str, group: int | None = None) -> None:
        if not lang.tts_lang or not text:
            return
        key = (group, text.lower())
        if group is not None and key in said:
            return  # same pronunciation, already has an icon
        said.add(key)
        speakables.append((text, lang.tts_lang))
        out.appendAttributedString_(attr(" ", rounded_font(11), theme.C_INK_SOFT))
        out.appendAttributedString_(speak_link(len(speakables) - 1))

    if not raw_text.strip():
        out.appendAttributedString_(
            attr(
                "( ˃̣̣̥ ⌓ ˂̣̣̥ )  nothing found\n",
                rounded_font(15, True),
                theme.C_DEEP,
                make_para(after=4),
            )
        )
        out.appendAttributedString_(
            attr(
                "Try covering a bit less text, zooming the page in, or nudging the "
                "frame so a whole line sits inside it. Check the language in the "
                "title bar matches the page, too.",
                rounded_font(11.5),
                theme.C_INK_SOFT,
                make_para(lead=3),
            )
        )
        return out, speakables

    out.appendAttributedString_(attr("read  ", rounded_font(10, True), theme.C_DEEP))
    out.appendAttributedString_(
        attr(raw_text, word_font(lang, 14), theme.C_INK, make_para(after=9, lead=3))
    )
    out.appendAttributedString_(attr(" ", rounded_font(11), theme.C_INK_SOFT))
    out.appendAttributedString_(copy_link())
    add_speaker(raw_text)
    out.appendAttributedString_(
        attr("\n", word_font(lang, 14), theme.C_INK, make_para(after=9, lead=3))
    )

    if not lang.has_script(raw_text):
        out.appendAttributedString_(
            attr(
                "No %s text in that — the frame may be over artwork, or the "
                "language picker may be set wrong." % lang.label,
                rounded_font(11.5),
                theme.C_INK_SOFT,
                make_para(lead=3),
            )
        )
        return out, speakables

    if not lang.ready:
        out.appendAttributedString_(
            attr(
                "loading the %s dictionary, one sec…" % lang.label,
                rounded_font(11.5),
                theme.C_INK_SOFT,
            )
        )
        return out, speakables

    para_word = make_para(head=26, before=8, after=1, lead=0)
    para_def = make_para(head=26, after=2, lead=2.0)

    for word in lang.words(raw_text):
        if not word.entries:
            out.appendAttributedString_(
                attr(word.surface + "  ", word_font(lang, 20), theme.C_INK, para_word)
            )
            out.appendAttributedString_(
                attr(
                    "not in the dictionary\n",
                    rounded_font(10.5),
                    theme.C_INK_SOFT,
                    para_word,
                )
            )
            continue

        for n, entry in enumerate(word.entries):
            # Headword and pronunciation share a line, so a speech bubble's
            # worth of vocabulary fits without scrolling.
            if n == 0:
                out.appendAttributedString_(
                    attr(
                        word.surface + "  ", word_font(lang, 20), theme.C_INK, para_word
                    )
                )
            else:
                out.appendAttributedString_(
                    attr("or  ", rounded_font(10), theme.C_INK_SOFT, para_word)
                )

            # Each pronunciation gets its own speaker, so a word with several
            # readings (那个 nà ge / nèi ge) can be heard either way.
            for r, reading in enumerate(entry.readings):
                if r:
                    out.appendAttributedString_(
                        attr("  · ", rounded_font(11), theme.C_INK_SOFT, para_word)
                    )
                if reading.label:
                    out.appendAttributedString_(
                        attr(
                            reading.label + " ",
                            rounded_font(11),
                            theme.C_INK_SOFT,
                            para_word,
                        )
                    )
                for i, (text, tone) in enumerate(reading.parts):
                    if i:
                        out.appendAttributedString_(
                            attr(" ", rounded_font(14.5), theme.C_INK_SOFT, para_word)
                        )
                    if tone in ("romaji", "label"):
                        out.appendAttributedString_(
                            attr(text, rounded_font(13), theme.C_INK_SOFT, para_word)
                        )
                    else:
                        color = TONE_COLORS.get(tone, theme.C_DEEP)
                        out.appendAttributedString_(
                            attr(text, rounded_font(14.5, True), color, para_word)
                        )
                add_speaker(reading.speech, group=id(word))

            if entry.note:
                out.appendAttributedString_(
                    attr(
                        "  " + entry.note,
                        word_font(lang, 12),
                        theme.C_INK_SOFT,
                        para_word,
                    )
                )
            out.appendAttributedString_(
                attr("\n", rounded_font(5), theme.C_INK, para_word)
            )

            for gloss in entry.glosses:
                out.appendAttributedString_(
                    attr(
                        "· " + lang.clean_gloss(gloss) + "\n",
                        rounded_font(11.5),
                        theme.C_INK_SOFT,
                        para_def,
                    )
                )

    if lang.code == "zh":
        out.appendAttributedString_(
            attr(
                "\ntones:  ",
                rounded_font(9.5, True),
                theme.C_INK_SOFT,
                make_para(before=8),
            )
        )
        for n, label in ((1, "1 ā"), (2, "2 á"), (3, "3 ǎ"), (4, "4 à"), (5, "5 a")):
            out.appendAttributedString_(
                attr(label + "   ", rounded_font(9.5, True), TONE_COLORS[n])
            )
    return out, speakables


GREETINGS: dict[str, str] = {
    "zh": "你好!",
    "ja": "こんにちは!",
    "ko": "안녕하세요!",
    "fr": "Bonjour !",
    "es": "¡Hola!",
    "it": "Ciao!",
    "de": "Hallo!",
    "pt": "Olá!",
    "cs": "Ahoj!",
    "tr": "Merhaba!",
    "la": "Salve!",
}


def welcome(lang: Language) -> NSMutableAttributedString:
    s = NSMutableAttributedString.alloc().init()
    s.appendAttributedString_(
        attr(
            GREETINGS.get(lang.code, "Hello!") + " ",
            word_font(lang, 17),
            theme.C_DEEP,
            make_para(after=4),
        )
    )
    s.appendAttributedString_(
        attr(
            "Drag me onto a word.\n",
            rounded_font(14, True),
            theme.C_DEEP,
            make_para(after=6),
        )
    )
    for line in (
        "Move the pink frame over Chinese text and let go — I read whatever "
        "is underneath and show pinyin + meanings here.",
        "Resize the frame with the three pink handles on it: the right edge "
        "for width, the bottom edge for height, the corner for both. Shrink it "
        "onto a single character, or open it out over a whole bubble.",
        "The ⤢ button has quick sizes — Character, Word, Line, Bubble.",
        "The globe button switches language: Chinese, Japanese, Korean, "
        "French, Spanish, Italian, German. Your choice is remembered.",
        "The magnifier button re-reads without moving; the chevron folds this "
        "panel away so only the frame is left.",
    ):
        s.appendAttributedString_(
            attr(
                "· " + line + "\n",
                rounded_font(11.5),
                theme.C_INK_SOFT,
                make_para(head=10, after=4, lead=2.5),
            )
        )
    if lang.code == "zh":
        s.appendAttributedString_(
            attr(
                "\nPinyin is colored by tone:  ",
                rounded_font(10, True),
                theme.C_INK_SOFT,
                make_para(before=6),
            )
        )
        for n, label in ((1, "mā"), (2, "má"), (3, "mǎ"), (4, "mà"), (5, "ma")):
            s.appendAttributedString_(
                attr(label + "  ", rounded_font(12, True), TONE_COLORS[n])
            )
    return s


def permission_notice(
    kind: Literal["translocated", "volume", "permission"],
) -> NSMutableAttributedString:
    """Attributed copy for Screen Recording / install-location failures."""
    body = NSMutableAttributedString.alloc().init()
    if kind in ("translocated", "volume"):
        body.appendAttributedString_(
            attr(
                "Please move Translation Lens to Applications\n",
                rounded_font(14, True),
                theme.C_DEEP,
                make_para(after=5),
            )
        )
        where = (
            "the disk image"
            if kind == "volume"
            else "a temporary location macOS created for it"
        )
        body.appendAttributedString_(
            attr(
                "Translation Lens is running from %s, and macOS will not "
                "remember the Screen Recording permission for an app there — "
                "you can grant it, but it is forgotten immediately.\n\n"
                "To fix it for good:\n"
                "1.  Quit Translation Lens.\n"
                "2.  Drag Translation Lens into your Applications folder.\n"
                "3.  Open it from Applications and allow Screen Recording.\n"
                "4.  Quit and open it once more.\n\n"
                "If it still asks after that, open Terminal and run:\n"
                'xattr -dr com.apple.quarantine "/Applications/Translation Lens.app"'
                % where,
                rounded_font(11.5),
                theme.C_INK_SOFT,
                make_para(lead=3),
            )
        )
        return body
    body.appendAttributedString_(
        attr(
            "Screen Recording permission needed\n",
            rounded_font(14, True),
            theme.C_DEEP,
            make_para(after=5),
        )
    )
    body.appendAttributedString_(
        attr(
            "System Settings → Privacy & Security → Screen & System Audio Recording, "
            "switch on “Translation Lens”, then quit and reopen the app.\n\n"
            "That permission is what lets the lens see the page underneath it.",
            rounded_font(11.5),
            theme.C_INK_SOFT,
            make_para(lead=3),
        )
    )
    return body
