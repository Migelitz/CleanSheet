from pathlib import Path
from types import SimpleNamespace
from typing import Self
from zipfile import ZipFile

import pytest

from cleansheet import diagnostics


def test_create_diagnostic_archive_includes_logs_and_environment_info(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    
    (tmp_path / "cleansheet.log").write_text("current log", encoding="utf-8")
    (tmp_path / "cleansheet.log.1").write_text("rotated log", encoding="utf-8")
    (tmp_path / "cleansheet.log.3").write_text("older log", encoding="utf-8")
    (tmp_path / "user-spreadsheet.csv").write_text("private data", encoding="utf-8")
    monkeypatch.setattr(diagnostics, "get_log_directory",lambda: tmp_path)

    archive_path = diagnostics.create_diagnostic_archive()

    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {
            "diagnostic-info.txt",
            "cleansheet.log",
            "cleansheet.log.1",
            "cleansheet.log.3",
        }
        assert archive.read("cleansheet.log") == b"current log"
        assert b"private data" not in archive.read("diagnostic-info.txt")


def test_create_diagnostic_archive_handles_missing_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    
    log_file = tmp_path / "missing" / "cleansheet.log"
    monkeypatch.setattr(diagnostics, "get_log_directory", lambda: log_file)

    archive_path = diagnostics.create_diagnostic_archive()

    assert archive_path.exists()
    with ZipFile(archive_path) as archive:
        assert archive.namelist() == ["diagnostic-info.txt"]


def test_create_diagnostic_archive_removes_partial_archive_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    
    log_file = tmp_path / "cleansheet.log"
    log_file.write_text("log", encoding="utf-8")
    monkeypatch.setattr(diagnostics, "get_log_directory", lambda: tmp_path)

    class FailingZipFile:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.path = Path(str(args[0]))

        def __enter__(self) -> Self:
            self.path.touch()
            raise OSError("archive unavailable")

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(diagnostics, "ZipFile", FailingZipFile)

    with pytest.raises(OSError, match="archive unavailable"):
        diagnostics.create_diagnostic_archive()

    assert not list(tmp_path.glob("cleansheet-diagnostics-*.zip"))


def test_open_diagnostic_directory_uses_linux_file_manager(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(diagnostics, "get_log_directory", lambda: tmp_path)
    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        diagnostics.subprocess,
        "run",
        lambda command, **kwargs: calls.append(command) or SimpleNamespace(returncode=0),
    )

    assert diagnostics.open_diagnostic_directory() is True
    assert calls == [["xdg-open", str(tmp_path)]]


def test_open_diagnostic_directory_rejects_unsupported_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diagnostics, "get_log_directory", lambda: tmp_path)
    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Plan9")

    assert diagnostics.open_diagnostic_directory() is False
