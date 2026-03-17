"""Crawler — directory walker, metadata capture, resume support."""

import hashlib
import os
import platform
import time
from pathlib import Path

from sweep.database import SweepDatabase, timestamp_to_utc
from sweep.errors import log_error
from sweep.progress import ProgressTracker


IS_WINDOWS = platform.system() == "Windows"


def _safe_stat(path: str) -> os.stat_result | None:
    """Get file stats, return None on error."""
    try:
        return os.stat(path)
    except OSError:
        return None


def _safe_lstat(entry: os.DirEntry) -> os.stat_result | None:
    """Get DirEntry stats without following symlinks, return None on error."""
    try:
        return entry.stat(follow_symlinks=False)
    except OSError:
        return None


def _long_path(path: str) -> str:
    """Prepend long path prefix on Windows if needed."""
    if IS_WINDOWS and len(path) > 250 and not path.startswith("\\\\?\\"):
        return "\\\\?\\" + path
    return path


def _hash_file(path: str, max_size: int = 10 * 1024 * 1024) -> str | None:
    """Compute MD5 hash of file. Returns None if file too large or error."""
    try:
        size = os.path.getsize(path)
        if size > max_size:
            return None
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def discover_directories(paths: list, skip_dirs: set, max_depth: int) -> list:
    """Walk all configured paths and return a flat list of directories to crawl.
    This is the 'map' phase — discover all work before starting."""
    all_dirs = []
    skip_lower = {s.lower() for s in skip_dirs}

    for root_path in paths:
        root_path = _long_path(root_path)
        if not os.path.isdir(root_path):
            continue

        for dirpath, dirnames, _ in os.walk(root_path, topdown=True):
            depth = dirpath.replace(root_path, "").count(os.sep)
            if depth >= max_depth:
                dirnames.clear()
                continue

            # Filter out skip dirs
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in skip_lower
            ]

            all_dirs.append(dirpath)

    return all_dirs


def crawl_directory(
    dir_path: str,
    db: SweepDatabase,
    hash_files: bool,
    skip_extensions: set,
    batch_size: int,
) -> tuple[int, int]:
    """Crawl a single directory (non-recursive — just its immediate contents).
    Returns (file_count, error_count)."""

    dir_path = _long_path(dir_path)
    file_count = 0
    error_count = 0
    file_batch = []

    # Insert the folder record
    dir_name = os.path.basename(dir_path) or dir_path
    parent = os.path.dirname(dir_path)

    dir_stat = _safe_stat(dir_path)
    dir_modified = timestamp_to_utc(dir_stat.st_mtime) if dir_stat else ""
    dir_created = ""
    if dir_stat:
        ctime = getattr(dir_stat, "st_birthtime", dir_stat.st_ctime)
        dir_created = timestamp_to_utc(ctime)

    folder_id = db.insert_folder(
        path=dir_path,
        name=dir_name,
        parent_path=parent,
        modified_at=dir_modified,
        created_at=dir_created,
    )

    # Scan directory contents (immediate children only)
    try:
        entries = list(os.scandir(dir_path))
    except OSError as exc:
        cat = log_error(exc, dir_path)
        db.log_error(dir_path, cat.value, str(exc))
        return 0, 1

    for entry in entries:
        if not entry.is_file(follow_symlinks=False):
            continue

        try:
            name = entry.name
            ext = os.path.splitext(name)[1].lower() if "." in name else ""

            if skip_extensions and ext in skip_extensions:
                continue

            stat = _safe_lstat(entry)
            if stat is None:
                error_count += 1
                db.log_error(entry.path, "UNKNOWN", "Could not stat file")
                continue

            file_path = _long_path(entry.path)
            modified = timestamp_to_utc(stat.st_mtime)
            ctime = getattr(stat, "st_birthtime", stat.st_ctime)
            created = timestamp_to_utc(ctime)

            content_hash = None
            if hash_files:
                content_hash = _hash_file(file_path)

            file_batch.append((
                folder_id, file_path, name, ext,
                stat.st_size, modified, created, content_hash,
            ))
            file_count += 1

            # Batch insert
            if len(file_batch) >= batch_size:
                db.insert_files_batch(file_batch)
                file_batch.clear()

        except Exception as exc:
            cat = log_error(exc, entry.path)
            db.log_error(entry.path, cat.value, str(exc))
            error_count += 1

    # Insert remaining files
    if file_batch:
        db.insert_files_batch(file_batch)

    return file_count, error_count


def run_crawl(config: dict, db: SweepDatabase, progress: ProgressTracker,
              dry_run: bool = False):
    """Main crawl loop — discover directories, crawl each, checkpoint."""

    paths = config["paths"]
    crawler_cfg = config["crawler"]
    skip_dirs = set(crawler_cfg["skip_dirs"])
    skip_extensions = {e.lower() for e in crawler_cfg.get("skip_extensions", [])}
    max_depth = crawler_cfg["max_depth"]
    throttle_ms = crawler_cfg["throttle_ms"]
    hash_files = crawler_cfg["hash_files"]
    batch_size = crawler_cfg["batch_commit_size"]

    # Phase 1: Discover all directories
    import logging
    logger = logging.getLogger("sweep")
    logger.info("Discovering directories...")
    all_dirs = discover_directories(paths, skip_dirs, max_depth)
    logger.info("Found %d directories to crawl", len(all_dirs))

    # Check which are already complete (resume support)
    completed = db.get_completed_dirs()
    pending = [d for d in all_dirs if d not in completed]

    if completed:
        logger.info("Resuming — %d already complete, %d remaining",
                     len(completed), len(pending))

    progress.set_total_dirs(len(all_dirs))
    progress.dirs_processed = len(completed)
    progress.write_status()

    if not pending:
        logger.info("All directories already crawled. Nothing to do.")
        return

    # Phase 2: Crawl each directory
    for dir_path in pending:
        if dry_run:
            progress.dir_complete(dir_path, 0, 0)
            continue

        # Mark in progress
        db.set_dir_state(dir_path, "in_progress")

        # Crawl
        file_count, error_count = crawl_directory(
            dir_path, db, hash_files, skip_extensions, batch_size,
        )

        # Mark complete and commit
        status = "complete" if error_count == 0 else "complete"
        db.set_dir_state(dir_path, status, file_count, error_count)
        db.commit()

        # Progress
        progress.dir_complete(dir_path, file_count, error_count)

        # Throttle
        if throttle_ms > 0:
            time.sleep(throttle_ms / 1000.0)

    progress.print_summary()
