import logging
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from cleansheet.logging_config import get_log_directory

logger = logging.getLogger(__name__)


def _diagnostic_archive_path(directory: Path) -> Path:
    """Return a timestamped archive path without overwriting an existing file."""

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    archive_path = directory / f"cleansheet-diagnostics-{timestamp}.zip"
    suffix = 1

    while archive_path.exists():
        archive_path = directory / f"cleansheet-diagnostics-{timestamp}-{suffix}.zip"
        suffix += 1

    return archive_path


def _environment_info() -> str:
    """Return non-sensitive runtime information for support diagnostics."""

    return (
        f"CleanSheet diagnostic package\n"
        f"Operating system: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\n"
    )


def create_diagnostic_archive() -> Path:
    """Create a ZIP containing CleanSheet logs and safe runtime information.

    Only the explicitly selected application log files are added. User data,
    arbitrary files, and the surrounding log directory are never archived.
    """

    log_directory = get_log_directory()
    log_directory.mkdir(parents=True, exist_ok=True)
    archive_path = _diagnostic_archive_path(log_directory)

    log_paths = sorted(path for path in log_directory.glob("cleansheet.log*") if path.is_file())

    try:
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("diagnostic-info.txt", _environment_info())

            for path in log_paths:
                archive.write(path, arcname=path.name)

    except Exception:
        logger.exception("Could not create diagnostic archive")

        try:
            archive_path.unlink(missing_ok=True)

        except OSError:
            logger.warning("Could not remove incomplete diagnostic archive", exc_info=True)
        raise

    logger.info(
        "Created diagnostic archive: files=%s archive=%s",
        len(log_paths),
        archive_path.name,
    )
    return archive_path


def open_diagnostic_directory() -> bool:
    """Open the CleanSheet log directory in the platform file manager."""

    directory = get_log_directory()

    try:
        directory.mkdir(parents=True, exist_ok=True)
        system = platform.system()

        if system == "Windows":
            os.startfile(str(directory))  # type: ignore[attr-defined]
        elif system == "Linux":
            result = subprocess.run(
                ["xdg-open", str(directory)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode != 0:
                logger.warning("Linux file manager declined to open log directory")
                return False
        else:
            logger.warning("Unsupported operating system for opening log directory: %s", system)
            return False

    except Exception:
        logger.exception("Could not open diagnostic log directory")
        return False

    logger.debug("Opened diagnostic log directory")
    return True
