#!/usr/bin/env python3
"""
Sweep — Filesystem Crawler & Catalog

Crawls filesystem paths, catalogs every file and folder, stores
metadata in SQLite. Resumable, throttled, standalone CLI.

Usage:
    python3 sweep.py --config config.json          # Start or resume crawl
    python3 sweep.py --config config.json --dry-run # Traverse without writing
    python3 sweep.py --status                       # Show crawl status
    python3 sweep.py --query "extension=.pdf"       # Query the catalog

Tracks: robota/wiki/plans/sweep-phase-1.md
"""

import argparse
import json
import os
import sys

from sweep import __version__
from sweep.config import load_config
from sweep.crawler import run_crawl
from sweep.database import SweepDatabase
from sweep.progress import ProgressTracker, setup_logging


def cmd_crawl(args):
    """Run or resume a crawl."""
    config = load_config(args.config)

    # Setup logging
    setup_logging(config["output"]["log_file"])

    import logging
    logger = logging.getLogger("sweep")
    logger.info("Sweep v%s — Filesystem Crawler & Catalog", __version__)
    logger.info("Config: %s", args.config)
    logger.info("Database: %s", config["output"]["database"])
    logger.info("Paths: %s", ", ".join(config["paths"]))
    logger.info("Throttle: %dms | Hash: %s | Max depth: %d",
                config["crawler"]["throttle_ms"],
                config["crawler"]["hash_files"],
                config["crawler"]["max_depth"])
    logger.info("")

    if config["crawler"]["throttle_ms"] == 0:
        logger.warning("*** THROTTLE IS DISABLED ***")
        logger.warning("Running at full speed against shared/network drives can")
        logger.warning("degrade the file server for other users.")
        logger.warning("If you don't need full speed, set throttle_ms in your config.")
        logger.warning("Starting in 5 seconds... (Ctrl+C to abort)")
        import time
        time.sleep(5)

    # Open database
    db = SweepDatabase(config["output"]["database"])

    # Setup progress tracking
    progress = ProgressTracker(
        status_file=config["output"]["status_file"],
        update_interval=10,
    )

    try:
        run_crawl(config, db, progress, dry_run=args.dry_run)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Interrupted by user. Progress saved — resume by running the same command.")
        progress.write_status()
    finally:
        db.close()


def cmd_status(args):
    """Show current crawl status."""
    # Try to find status file
    status_file = "sweep-status.json"
    db_file = "sweep.db"

    if args.config:
        config = load_config(args.config)
        status_file = config["output"]["status_file"]
        db_file = config["output"]["database"]

    # Read status file if it exists
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            status = json.load(f)
        print(f"Status:      {status.get('status', 'unknown')}")
        print(f"Started:     {status.get('started_at', 'unknown')}")
        print(f"Elapsed:     {status.get('elapsed_human', 'unknown')}")
        print(f"Dirs:        {status.get('dirs_processed', 0)}/{status.get('dirs_total', 0)}")
        print(f"Files:       {status.get('files_found', 0)}")
        print(f"Errors:      {status.get('errors_logged', 0)}")
        print(f"Current:     {status.get('current_path', 'N/A')}")
        if status.get("eta_human"):
            print(f"ETA:         {status['eta_human']}")
        print(f"Updated:     {status.get('updated_at', 'unknown')}")
    elif os.path.exists(db_file):
        # Fall back to querying the database
        db = SweepDatabase(db_file)
        stats = db.get_crawl_stats()
        db.close()
        print(f"Files:       {stats['total_files']}")
        print(f"Folders:     {stats['total_folders']}")
        print(f"Errors:      {stats['total_errors']}")
        print(f"Dirs done:   {stats['dirs_complete']}")
        print(f"Dirs left:   {stats['dirs_pending'] + stats['dirs_in_progress']}")
    else:
        print("No crawl data found. Run a crawl first.")
        sys.exit(1)


def cmd_query(args):
    """Query the file catalog."""
    db_file = "sweep.db"
    if args.config:
        config = load_config(args.config)
        db_file = config["output"]["database"]

    if not os.path.exists(db_file):
        print(f"Database not found: {db_file}")
        sys.exit(1)

    db = SweepDatabase(db_file)

    # Parse query string: "extension=.pdf", "path=/mnt/d", "size>1000000"
    kwargs = {}
    for part in args.query.split(","):
        part = part.strip()
        if "=" in part:
            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key == "extension":
                kwargs["extension"] = val
            elif key == "path":
                kwargs["path_prefix"] = val
            elif key == "min_size":
                kwargs["min_size"] = int(val)
            elif key == "max_size":
                kwargs["max_size"] = int(val)

    if args.limit:
        kwargs["limit"] = args.limit

    results = db.query_files(**kwargs)
    db.close()

    if not results:
        print("No files match the query.")
        return

    # Print formatted table
    print(f"{'Path':<80} {'Size':>10} {'Modified':<20}")
    print("-" * 112)
    for r in results:
        size_str = _format_size(r["size_bytes"]) if r["size_bytes"] else "-"
        mod = (r["modified_at"] or "-")[:19]
        path = r["path"]
        if len(path) > 78:
            path = "..." + path[-75:]
        print(f"{path:<80} {size_str:>10} {mod:<20}")

    print(f"\n{len(results)} result(s)")


def _format_size(size_bytes):
    """Human-readable file size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def main():
    parser = argparse.ArgumentParser(
        prog="sweep",
        description="Sweep — Filesystem Crawler & Catalog. "
                    "Crawls paths, catalogs files, stores in SQLite. "
                    "Resumable, throttled, standalone.",
    )
    parser.add_argument("--version", action="version",
                        version=f"sweep {__version__}")
    parser.add_argument("--config", "-c", default=None,
                        help="Path to config.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Traverse directories but don't write to database")
    parser.add_argument("--status", action="store_true",
                        help="Show current crawl status and exit")
    parser.add_argument("--query", "-q", default=None,
                        help='Query the catalog (e.g., "extension=.pdf,path=/mnt/d")')
    parser.add_argument("--limit", type=int, default=100,
                        help="Max results for query (default: 100)")

    args = parser.parse_args()

    if args.status:
        cmd_status(args)
    elif args.query:
        cmd_query(args)
    elif args.config:
        cmd_crawl(args)
    else:
        parser.print_help()
        print("\nQuick start:")
        print("  cp config.template.json config.json")
        print("  # Edit config.json — set your paths")
        print("  python3 sweep.py --config config.json")


if __name__ == "__main__":
    main()
