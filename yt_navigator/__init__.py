"""YouTube Navigator package."""

import importlib.metadata
import os
from pathlib import Path

# Try to get version from version.txt when in development
# or from package metadata when installed
try:
    # First try to get version from package metadata (when installed)
    __version__ = importlib.metadata.version("yt_navigator")
except importlib.metadata.PackageNotFoundError:
    # If not installed, read from version.txt
    version_file = Path(__file__).parent.parent / "version.txt"
    if version_file.exists():
        __version__ = version_file.read_text().strip()
    else:
        __version__ = "unknown"
