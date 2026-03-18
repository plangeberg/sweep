# Sweep

> *Know what you have. Find what you need. Stop losing files in the pile.*

---

## The Problem

You hoard data to avoid losing it, then lose data because you have too much stuff — 2, 3, 4 copies of the same thing scattered across drives and network shares. Millions of files. No inventory. No way to answer "where is that document?" without spelunking through File Explorer.

## The Solution

Sweep crawls your drives, catalogs every file and folder into a searchable database, and gives you a complete inventory of what exists where. Run it once, walk away for days, come back to answers.

## Key Features

- **Set it and forget it** — one command, runs unattended for hours or days
- **Unkillable** — survives crashes, power loss, unplugs. Picks up exactly where it stopped.
- **Network-safe** — configurable throttle keeps IT happy
- **Find anything** — query by extension, path, or size from the command line
- **Zero dependencies** — Python stdlib only. Copy it anywhere and run.
- **Two environments, one tool** — home (full speed, dedup) and work (throttled, catalog-only) via config

## What It's NOT

- Not a file sync tool (it doesn't move or copy files)
- Not a backup tool (it catalogs, it doesn't protect)
- Not a search engine (no full-text content search — metadata only)
- Not a dedup tool (it *finds* duplicates — it doesn't delete them)

## Screenshots / Screens

| Screen | What You See | What You Do |
|--------|-------------|-------------|
| Start crawl | Config summary, path list, throttle settings | `python3 sweep.py -c config.json` |
| Progress | `DIR 1234/5000 \| 45000 files \| 3 errors \| /path/to/current` | Watch or walk away |
| Status check | Dirs done, files found, errors, ETA | `cat sweep-status.json` |
| Query | Formatted table of matching files with path, size, date | `python3 sweep.py -q "extension=.pdf"` |
| Resume | "Resuming — 1234 already complete, 3766 remaining" | Same start command |

## Quick Start

```bash
git clone https://github.com/plangeberg/sweep.git
cd sweep/
cp config.template.json config.json
# Edit config.json — set your paths
python3 sweep.py --config config.json
```

## Tech Stack

Python 3.10+ (stdlib only) + SQLite with WAL mode. No install, no dependencies.

## Status

**Active** — Phase 1 shipped. Phase 2 (web viewer with pruning, tagging, search) planned.

---

> **Playbook**: See README.md in project root
> **Repo**: [GitHub](https://github.com/plangeberg/sweep)
