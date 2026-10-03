import logging
import os
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/Migelitz/CleanSheet/releases/latest"

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")

@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_url: str

    @property
    def update_available(self) -> bool:
        return parse_version(self.latest_version) > parse_version(self.current_version)


def get_current_version() -> str:
    """Return the installed CleanSheet version."""

    try:
        return f"v{version("CleanSheet")}"
    except PackageNotFoundError:
        logger.exception("Could not determine CleanSheet package version")
        return "0.0.0"


def parse_version(version_string: str) -> tuple[int, int, int]:
    """Convert a simple semantic version such as 'v1.2.3' into a tuple."""

    cleaned = version_string.strip().lstrip("vV")
    parts = cleaned.split(".")

    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_string}")

    try:
        return tuple(int(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"Invalid version format: {version_string}") from exc


def check_for_update() -> UpdateInfo | None:
    """Check GitHub for the latest CleanSheet release."""

    current_version = get_current_version()

    try:
        response = requests.get(
            GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "CleanSheet-Updater",
                "Authorization": f"Bearer {TOKEN}"
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        latest_version = data["tag_name"]
        release_url = data["html_url"]

        update_info = UpdateInfo(
            current_version=current_version,
            latest_version=latest_version,
            release_url=release_url,
        )

        logger.info(
            "Update check completed: current=%s, latest=%s, update_available=%s",
            update_info.current_version,
            update_info.latest_version,
            update_info.update_available,
        )

        return update_info
    
    except requests.RequestException:
        logger.warning("Could not check for CleanSheet updates.", exc_info=True)
        return None

    except (KeyError, TypeError, ValueError):
        logger.warning("Github returned an unexpected release response.", exc_info=True)
        return None