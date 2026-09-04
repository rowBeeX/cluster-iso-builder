"""Farbige Abschnitts- und Schritt-Überschriften für den Installer."""

from __future__ import annotations

import sys

_RESET = "\033[0m"
_BOLD = "\033[1m"
_CYAN = "\033[36m"


def _is_tty() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class Logger:
    """Gibt farbige Überschriften im Terminal aus, unfarbig sonst."""

    def __init__(self) -> None:
        self._use_color = _is_tty()

    def _c(self, color: str, text: str) -> str:
        return f"{color}{text}{_RESET}" if self._use_color else text

    def section(self, title: str) -> None:
        print(self._c(_BOLD + _CYAN, f"\n==> {title}"), flush=True)

    def step(self, title: str) -> None:
        print(self._c(_BOLD, f"--- {title}"), flush=True)
