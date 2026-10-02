from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

_SOURCE_ASSETS = BASE_DIR.parents[1] / "assets"
_PACKAGED_ASSETS = BASE_DIR / "assets"

# Check if the assets is inside of package (src/cleansheet)
if _PACKAGED_ASSETS.is_dir():
    ASSETS_DIR = _PACKAGED_ASSETS

# Check if the assets is inside of root (cleansheet/)
elif _SOURCE_ASSETS.is_dir():
    ASSETS_DIR = _SOURCE_ASSETS
else:
    raise FileNotFoundError("CleanSheet assets directory not found.")