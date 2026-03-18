# Sweep — File Map

> Updated every session that touches this repo.

| File/Dir | Purpose |
|----------|---------|
| `README.md` | **Start here** — what it is, how to use it, quick reference |
| `project.json` | Single-source project identity |
| `CLAUDE.md` | Project context for Claude Code sessions |
| `STRUCTURE.md` | This file |
| `.gitignore` | Git ignores (incl. config.json, *.db, logs) |
| `config.template.json` | Config template with documented defaults |
| **Code** | |
| `sweep.py` | Main CLI entry point |
| `sweep/__init__.py` | Package init + version |
| `sweep/config.py` | Config loader, validator, template/override merge |
| `sweep/crawler.py` | Directory walker, metadata capture, resume, throttle |
| `sweep/database.py` | SQLite schema, WAL mode, CRUD operations, queries |
| `sweep/errors.py` | Error taxonomy (8 categories), classify + log |
| `sweep/progress.py` | Status file, log file, console output, ETA |
| **Docs** | |
| `docs/brochure.md` | What is Sweep, what it does, what it's NOT for |
| `docs/sweep.html` | Dropzone landing page (dark theme, standalone) |
| `docs/technical/schema.md` | SQLite database schema reference |
| `docs/technical/error-categories.md` | Error taxonomy with query examples |
| **Other** | |
| `tests/` | Test suite (TBD) |
| `.gitlab/issue_templates/Bug.md` | Bug report template |
| `.gitlab/issue_templates/Story.md` | Feature story template |
