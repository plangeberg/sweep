# Sweep — Filesystem Crawler & Catalog

> Behavioral guidelines: Read `/mnt/d/SynologyDrive/czechito/brain/COS-CORE.md`

## What Is This

Sweep crawls filesystem paths (local drives, UNC shares, SharePoint via WebDAV), catalogs every file and folder with metadata, and stores results in a SQLite database. It's a standalone Python CLI — no dependencies beyond stdlib, no Claude Code required at runtime. Designed to run unattended for days across millions of files, surviving interruptions and resuming where it left off.

Phase 1 is crawler only. Phase 2 adds a reactive web viewer with pruning, tagging, and search. Phase 3 adds NorthStar checklist linkage and MCP server integration.

## Where Does It Run
- **Machine**: Deadpool (home), Cable (work)
- **Port**: N/A (CLI tool, no server in Phase 1)
- **URL**: N/A
- **Domain**: N/A

## How to Install / Deploy
```bash
# No installation — Python stdlib only
cd /mnt/d/SynologyDrive/czechito/sweep/

# Create config from template
cp config.template.json config.json
# Edit config.json — set your paths
```

## How to Configure
| Setting | File | Description | Default |
|---------|------|-------------|---------|
| `paths` | `config.json` | List of filesystem paths to crawl | (must set) |
| `output.database` | `config.json` | SQLite database file path | `sweep.db` |
| `output.log_file` | `config.json` | Append-only log file | `sweep.log` |
| `output.status_file` | `config.json` | JSON status file (machine-readable) | `sweep-status.json` |
| `crawler.throttle_ms` | `config.json` | Pause between directories (ms). 0 = full speed. | `0` |
| `crawler.hash_files` | `config.json` | Compute content hash per file (for dedup) | `false` |
| `crawler.max_depth` | `config.json` | Maximum directory recursion depth | `20` |
| `crawler.skip_dirs` | `config.json` | Directory names to skip (case-insensitive) | See template |
| `crawler.skip_extensions` | `config.json` | File extensions to skip | `[]` |
| `crawler.batch_commit_size` | `config.json` | Files per SQLite transaction | `500` |

### Home config example
```json
{
  "paths": ["/mnt/c", "/mnt/d"],
  "crawler": { "throttle_ms": 0, "hash_files": true }
}
```

### Cable config example
```json
{
  "paths": ["\\\\server\\share\\ProjectA", "\\\\server\\share\\ProjectB"],
  "crawler": { "throttle_ms": 500, "hash_files": false }
}
```

**Why throttle on Cable**: Sweep crawls UNC shares (shared network drives). Running flat out can generate enough I/O to degrade the file server for other users. `throttle_ms: 500` adds a half-second pause between directories to keep the load invisible. Do not set to 0 on shared infrastructure.

## How to Run
```bash
# First run — starts fresh crawl
python3 sweep.py --config config.json

# Resume after interruption — auto-detects incomplete state
python3 sweep.py --config config.json

# Check status without running
python3 sweep.py --status

# Dry run — traverse but don't write to DB
python3 sweep.py --config config.json --dry-run
```

## How to Use

1. Copy `config.template.json` to `config.json`
2. Set your paths in `config.json`
3. Run `python3 sweep.py --config config.json`
4. Check progress: `tail -f sweep.log` or `cat sweep-status.json`
5. Kill anytime (Ctrl+C, close terminal, blue screen) — it resumes automatically
6. Query results: `python3 sweep.py --query "extension=.pdf"`

## How to Verify It Works
```bash
# Create a small test tree
mkdir -p /tmp/sweep-test/sub1/sub2
echo "hello" > /tmp/sweep-test/file1.txt
echo "world" > /tmp/sweep-test/sub1/file2.pdf

# Run against it
python3 sweep.py --config <(echo '{"paths": ["/tmp/sweep-test"], "output": {"database": "/tmp/sweep-test.db"}}')

# Check DB has entries
python3 -c "import sqlite3; db=sqlite3.connect('/tmp/sweep-test.db'); print(db.execute('SELECT COUNT(*) FROM files').fetchone())"
# Expected: (2,)
```

## Architecture

### Tech Stack
- Python 3.10+ (stdlib only — no pip, no venv)
- SQLite 3 with WAL mode (crash-safe, single file)
- `os.scandir()` for performant directory traversal
- `pathlib` for cross-platform path handling
- `argparse` for CLI
- `logging` for structured log output

### Data Flow
```
config.json → sweep.py → os.scandir() → SQLite (sweep.db)
                                       → sweep.log (append-only)
                                       → sweep-status.json (overwritten per batch)
```

### Resume Strategy
Directory-level checkpointing via `crawl_state` table in SQLite. Each directory is marked `pending` → `in_progress` → `complete`. On restart, skip completed directories. Partial directories re-scanned (acceptable — worst case re-scans one folder).

### Error Handling
Never crash, never prompt. Every error: log category + path + message, skip, continue.
Categories: `PERMISSION`, `SYMLINK`, `LOCKED`, `NETWORK`, `PATH_TOO_LONG`, `ENCODING`, `TIMEOUT`, `UNKNOWN`.

## Repo Structure
```
sweep/
├── project.json              — project identity
├── CLAUDE.md                 — this file
├── STRUCTURE.md              — file map
├── .gitignore                — ignores (incl. config.json, *.db, logs)
├── config.template.json      — config template with REPLACE_ME placeholders
├── sweep.py                  — main CLI entry point
├── sweep/                    — package directory
│   ├── __init__.py
│   ├── config.py             — config loader + validator
│   ├── crawler.py            — directory walker + metadata capture
│   ├── database.py           — SQLite schema + operations
│   ├── progress.py           — status file + log file + console output
│   └── errors.py             — error taxonomy + handler
├── tests/
│   ├── test_config.py
│   ├── test_crawler.py
│   ├── test_database.py
│   └── test_resume.py
└── .gitlab/
    └── issue_templates/
        ├── Bug.md
        └── Story.md
```

## GitLab / GitHub
- **GitLab**: `tcdz/sweep`
- **GitHub**: `plangeberg/sweep`
- **Issues**: Track all work on GitLab issues

## Session Protocol
1. Read this CLAUDE.md
2. Check `brain/turnovers/` for pending turnovers
3. Check GitLab issues for current sprint/priority
4. Pick up from where last session left off
5. End: run /turnover

## Commit Style
Short message + `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>`

## Rules
- No work without a GitLab issue
- Docs update in the same commit as code changes
- Python stdlib only — no pip dependencies
- Never crash on errors — log and skip
- Never prompt for user input — all config upfront
- Config uses template/override pattern (config.template.json → config.json)

## Key References
- **Robota pipeline**: `robota/wiki/plans/sweep-phase-1.md` — full PM plan with milestones, schema, decisions
- **PO approval**: `robota/wiki/approved/sweep.md` — acceptance criteria, constraints, risks
- **Intake brief**: `robota/wiki/intake/sweep.md` — original requirements
- **Prior art**: `home/scripts/python/project-inventory/inventory.py` — working crawler with resume pattern
