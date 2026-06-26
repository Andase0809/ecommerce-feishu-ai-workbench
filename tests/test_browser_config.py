from pathlib import Path

import pytest

from src.browser_config import find_browser_path, resolve_browser_path


def test_resolve_browser_path_accepts_explicit_path(tmp_path) -> None:
    chrome = tmp_path / "chrome.exe"
    chrome.write_text("", encoding="utf-8")

    result = resolve_browser_path("auto", chrome)

    assert result.browser == "chrome"
    assert result.path == chrome
    assert result.source == "explicit"


def test_resolve_browser_path_rejects_missing_explicit_path(tmp_path) -> None:
    missing = tmp_path / "missing.exe"

    with pytest.raises(FileNotFoundError, match="浏览器路径不存在"):
        resolve_browser_path("auto", missing)


def test_find_browser_path_scans_program_files_for_chrome(tmp_path, monkeypatch) -> None:
    chrome = tmp_path / "Google" / "Chrome" / "Application" / "chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.write_text("", encoding="utf-8")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "x86"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setattr("shutil.which", lambda command: None)

    assert find_browser_path("chrome") == chrome
