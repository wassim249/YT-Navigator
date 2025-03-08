"""Logging utilities for the yt_navigator project."""

import os
from datetime import datetime


def get_log_filename(base_dir):
    """Generate a log filename with today's date.

    Args:
        base_dir: The directory where logs are stored
        prefix: The prefix for the log filename

    Returns:
        str: The full path to the log file with today's date
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(base_dir, f"{today}.jsonl")
