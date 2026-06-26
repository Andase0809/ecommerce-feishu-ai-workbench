from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


BrowserChoice = Literal["auto", "chrome", "edge"]


@dataclass(frozen=True)
class BrowserPathResult:
    browser: str
    path: Path | None
    source: str


def resolve_browser_path(
    browser: BrowserChoice = "auto",
    browser_path: str | Path | None = None,
) -> BrowserPathResult:
    explicit = str(browser_path or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"浏览器路径不存在：{path}")
        return BrowserPathResult(browser=_infer_browser_name(path, browser), path=path, source="explicit")

    for candidate_browser in _browser_order(browser):
        path = find_browser_path(candidate_browser)
        if path:
            return BrowserPathResult(browser=candidate_browser, path=path, source="auto")
    return BrowserPathResult(browser=browser, path=None, source="not_found")


def find_browser_path(browser: Literal["chrome", "edge"]) -> Path | None:
    for candidate in _candidate_paths(browser):
        if candidate.exists():
            return candidate
    for command in _candidate_commands(browser):
        resolved = shutil.which(command)
        if resolved:
            return Path(resolved)
    return None


def _browser_order(browser: BrowserChoice) -> list[Literal["chrome", "edge"]]:
    if browser == "chrome":
        return ["chrome"]
    if browser == "edge":
        return ["edge"]
    return ["chrome", "edge"]


def _candidate_paths(browser: Literal["chrome", "edge"]) -> list[Path]:
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if browser == "chrome":
        return [
            Path(program_files) / "Google/Chrome/Application/chrome.exe",
            Path(program_files_x86) / "Google/Chrome/Application/chrome.exe",
            Path(local_app_data) / "Google/Chrome/Application/chrome.exe",
        ]
    return [
        Path(program_files) / "Microsoft/Edge/Application/msedge.exe",
        Path(program_files_x86) / "Microsoft/Edge/Application/msedge.exe",
        Path(local_app_data) / "Microsoft/Edge/Application/msedge.exe",
    ]


def _candidate_commands(browser: Literal["chrome", "edge"]) -> list[str]:
    if browser == "chrome":
        return ["chrome.exe", "chrome", "google-chrome", "google-chrome-stable"]
    return ["msedge.exe", "msedge", "microsoft-edge"]


def _infer_browser_name(path: Path, browser: BrowserChoice) -> str:
    if browser != "auto":
        return browser
    name = path.name.lower()
    if "msedge" in name or "edge" in name:
        return "edge"
    if "chrome" in name:
        return "chrome"
    return "custom"
