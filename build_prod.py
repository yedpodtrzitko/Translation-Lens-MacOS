"""Production build of Translation Lens.app via PyInstaller."""

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.__main__ import run as pyinstaller_run

_ROOT = Path(__file__).resolve().parent
_SPEC = _ROOT / "TranslationLens.spec"


def main() -> None:
    os.chdir(_ROOT)
    pyinstaller_run([str(_SPEC), "--noconfirm"])


if __name__ == "__main__":
    main()
