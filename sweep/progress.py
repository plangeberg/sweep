"""Progress reporting — status file, log file, console output."""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone


logger = logging.getLogger("sweep")


def setup_logging(log_file: str):
    """Configure logging to file and console."""
    root = logging.getLogger("sweep")
    root.setLevel(logging.INFO)

    # File handler — append, detailed
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(fh)

    # Console handler — compact
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(ch)


class ProgressTracker:
    """Tracks and reports crawl progress."""

    def __init__(self, status_file: str, update_interval: int = 10):
        self.status_file = status_file
        self.update_interval = update_interval  # write status every N directories
        self.start_time = time.time()
        self.dirs_processed = 0
        self.dirs_total = 0
        self.files_found = 0
        self.errors_logged = 0
        self.current_path = ""
        self._last_write = 0

    def set_total_dirs(self, total: int):
        """Set total directory count for ETA calculation."""
        self.dirs_total = total

    def dir_complete(self, path: str, file_count: int, error_count: int):
        """Record a completed directory."""
        self.dirs_processed += 1
        self.files_found += file_count
        self.errors_logged += error_count
        self.current_path = path

        # Log one line per directory
        elapsed = time.time() - self.start_time
        logger.info(
            "DIR %d/%d | %d files | %d errors | %s",
            self.dirs_processed,
            self.dirs_total,
            self.files_found,
            self.errors_logged,
            _truncate_path(path, 60),
        )

        # Write status file periodically
        if self.dirs_processed - self._last_write >= self.update_interval:
            self.write_status()
            self._last_write = self.dirs_processed

    def write_status(self):
        """Write machine-readable status file."""
        elapsed = time.time() - self.start_time
        eta_seconds = None
        if self.dirs_processed > 0 and self.dirs_total > 0:
            rate = elapsed / self.dirs_processed
            remaining = self.dirs_total - self.dirs_processed
            eta_seconds = int(rate * remaining)

        status = {
            "status": "running" if self.dirs_processed < self.dirs_total else "complete",
            "started_at": datetime.fromtimestamp(
                self.start_time, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "elapsed_seconds": int(elapsed),
            "elapsed_human": _format_duration(int(elapsed)),
            "dirs_processed": self.dirs_processed,
            "dirs_total": self.dirs_total,
            "dirs_remaining": self.dirs_total - self.dirs_processed,
            "files_found": self.files_found,
            "errors_logged": self.errors_logged,
            "current_path": self.current_path,
            "eta_seconds": eta_seconds,
            "eta_human": _format_duration(eta_seconds) if eta_seconds else None,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        try:
            tmp = self.status_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
            os.replace(tmp, self.status_file)
        except OSError:
            pass  # status file is best-effort

    def print_summary(self):
        """Print final summary to console."""
        elapsed = time.time() - self.start_time
        logger.info("")
        logger.info("=" * 60)
        logger.info("  SWEEP COMPLETE")
        logger.info("  Directories:  %d", self.dirs_processed)
        logger.info("  Files:        %d", self.files_found)
        logger.info("  Errors:       %d", self.errors_logged)
        logger.info("  Elapsed:      %s", _format_duration(int(elapsed)))
        if self.files_found > 0 and elapsed > 0:
            logger.info("  Rate:         %.0f files/sec", self.files_found / elapsed)
        logger.info("=" * 60)
        self.write_status()


def _truncate_path(path: str, max_len: int) -> str:
    """Truncate path for display, keeping the end visible."""
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3):]


def _format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds is None:
        return "unknown"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"
