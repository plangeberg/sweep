# Sweep

> **Know what you have. Find what you need. Stop losing files in the pile.**

---

## The Problem

You hoard data to avoid losing it, then lose data because you have too much. 2, 3, 4 copies of the same thing scattered across drives and network shares. Millions of files across dozens of folders. No way to know what's where without manually clicking through File Explorer for hours. When someone asks "do you have the SRR documents?" you know they're *somewhere* — but where?

## The Solution

Sweep crawls your drives and network shares, catalogs every file and folder, and stores the results in a searchable database. Run it once, walk away, come back to a complete inventory. Kill it anytime — it picks up where it left off. Query it from the command line. Phase 2 adds a web viewer with pruning, tagging, and search.

## Key Features

- **Set it and forget it** — point it at paths, run one command, walk away. It runs for hours or days unattended.
- **Unkillable** — blue screen, power outage, laptop unplugged, Ctrl+C. Doesn't matter. It resumes exactly where it stopped.
- **Network-safe** — configurable throttle so you don't hammer shared drives or get flagged by IT.
- **Find anything** — query by file extension, path, or size. "Show me all .pdf files under this path."
- **Zero dependencies** — Python stdlib only. No pip install, no venv, no admin rights. Copy it anywhere and run.
- **Two environments, one tool** — home mode (full speed, hash for dedup) and work mode (throttled, no hash) via config.

## What It's NOT

- Not a file sync tool (it doesn't move or copy files)
- Not a backup tool (it catalogs, it doesn't protect)
- Not a search engine (no full-text content search — it searches metadata: names, paths, extensions, sizes)
- Not a dedup tool (it *finds* duplicates via hashing — it doesn't delete them)
- Phase 1 is CLI only — no web UI yet

## Quick Reference

| What | Command |
|------|---------|
| **Start a crawl** | `python3 sweep.py -c config.json` |
| **Resume a crawl** | `python3 sweep.py -c config.json` (same command — auto-resumes) |
| **Check progress** | `python3 sweep.py --status` |
| **Watch live** | `tail -f sweep.log` |
| **Quick status** | `cat sweep-status.json` |
| **Find PDFs** | `python3 sweep.py -q "extension=.pdf"` |
| **Find large files** | `python3 sweep.py -q "min_size=100000000"` |
| **Find by path** | `python3 sweep.py -q "path=/mnt/d/Projects"` |
| **Dry run** | `python3 sweep.py -c config.json --dry-run` |
| **Version** | `python3 sweep.py --version` |
| **Help** | `python3 sweep.py --help` |

## Setup (2 minutes)

```bash
# 1. Go to the sweep directory
cd /mnt/d/SynologyDrive/czechito/sweep/

# 2. Copy the config template
cp config.template.json config.json

# 3. Edit config.json — set your paths
#    Home example:  "paths": ["/mnt/c", "/mnt/d"]
#    Work example:  "paths": ["\\\\server\\share\\ProjectA"]

# 4. Run it
python3 sweep.py --config config.json

# 5. Check on it later
cat sweep-status.json
```

## Configuration

Edit `config.json` (copy from `config.template.json` first):

| Setting | What It Does | Home | Work |
|---------|-------------|------|------|
| `paths` | What to crawl | Your local drives | UNC/SharePoint paths |
| `throttle_ms` | Pause between folders (ms) | `0` (full speed) | `500` (be polite) |
| `hash_files` | Compute file hashes for dedup | `true` | `false` |
| `max_depth` | How deep to recurse | `20` | `20` |
| `skip_dirs` | Folder names to skip | node_modules, .git, etc. | Same + your skips |
| `batch_commit_size` | Files per DB write | `500` | `500` |

## Output Files

| File | What It Is | How to Read |
|------|-----------|-------------|
| `sweep.db` | The catalog (SQLite) | `python3 sweep.py -q "extension=.pdf"` |
| `sweep.log` | Detailed log (append-only) | `tail -f sweep.log` |
| `sweep-status.json` | Machine-readable progress | `cat sweep-status.json` |

## Tech Stack

Python 3.10+ (stdlib only) + SQLite with WAL mode. No dependencies, no install.

## Status

**Active** — Phase 1 MVP shipped. Crawler, resume, throttle, query, progress all working.

---

> **Full path**: `D:\SynologyDrive\czechito\sweep\`
> **Repo**: [GitLab](http://192.168.2.13:8929/tcdz/sweep) | [GitHub](https://github.com/plangeberg/sweep)
> **Issues**: [sweep#1](http://192.168.2.13:8929/tcdz/sweep/-/issues/1)
> **Pipeline docs**: `robota/wiki/` (PO approval, PM plan, engineer notes)
