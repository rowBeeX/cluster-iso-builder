"""Farbiges Logging mit optionaler Log-Datei-Ausgabe."""

from __future__ import annotations

import sys
from pathlib import Path

_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"


def _is_tty() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class Logger:
    """Logger mit ANSI-Farben im Terminal und optionaler Log-Datei."""

    def __init__(self, log_file: Path | None = None) -> None:
        self._use_color = _is_tty()
        self._fh = None
        self.errors = 0

        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            self._fh = log_file.open("a", encoding="utf-8")

    def _c(self, color: str, text: str) -> str:
        if self._use_color:
            return f"{color}{text}{_RESET}"
        return text

    def _emit(self, line: str, plain: str | None = None) -> None:
        print(line, flush=True)
        if self._fh is not None:
            print(plain or line, file=self._fh, flush=True)

    def info(self, msg: str) -> None:
        self._emit(msg)

    def section(self, title: str) -> None:
        colored = self._c(_BOLD + _CYAN, f"\n==> {title}")
        self._emit(colored, f"\n==> {title}")

    def step(self, title: str) -> None:
        colored = self._c(_BOLD, f"--- {title}")
        self._emit(colored, f"--- {title}")

    def ok(self, msg: str) -> None:
        colored = f"{self._c(_GREEN, 'ok')}: {msg}"
        self._emit(colored, f"ok: {msg}")

    def fail(self, msg: str) -> None:
        self.errors += 1
        colored = f"{self._c(_RED + _BOLD, 'FAIL')}: {msg}"
        print(colored, flush=True, file=sys.stderr)
        if self._fh is not None:
            print(f"FAIL: {msg}", file=self._fh, flush=True)

    def warn(self, msg: str) -> None:
        colored = f"{self._c(_YELLOW, 'WARN')}: {msg}"
        self._emit(colored, f"WARN: {msg}")

    def passed(self, msg: str) -> None:
        colored = f"{self._c(_GREEN + _BOLD, '[PASS]')} {msg}"
        self._emit(colored, f"[PASS] {msg}")

    def failed(self, msg: str) -> None:
        self.errors += 1
        colored = f"{self._c(_RED + _BOLD, '[FAIL]')} {msg}"
        print(colored, flush=True, file=sys.stderr)
        if self._fh is not None:
            print(f"[FAIL] {msg}", file=self._fh, flush=True)

    def summary_ok(self, what: str) -> None:
        colored = self._c(_GREEN + _BOLD, f"{what} OK.")
        self._emit(colored, f"{what} OK.")

    def summary_fail(self, what: str, count: int) -> None:
        msg = f"{what} FAILED: {count} Fehler."
        colored = self._c(_RED + _BOLD, msg)
        print(colored, flush=True, file=sys.stderr)
        if self._fh is not None:
            print(msg, file=self._fh, flush=True)

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> Logger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
