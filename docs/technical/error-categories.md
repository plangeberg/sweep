# Sweep — Error Categories

When Sweep encounters an error, it classifies it, logs it, and continues. It never stops.

| Category | What Triggers It | Example |
|----------|-----------------|---------|
| `PERMISSION` | Access denied to file or folder | Protected system folders, admin-only files |
| `SYMLINK` | Broken or circular symbolic link | Dangling symlink pointing to deleted target |
| `LOCKED` | File locked by another process | Open Excel file, database lock |
| `NETWORK` | Network share unreachable | UNC path timeout, disconnected share |
| `PATH_TOO_LONG` | Path exceeds OS limit (260 chars on Windows) | Deeply nested node_modules |
| `ENCODING` | Filename has unreadable characters | Non-UTF8 filenames from legacy systems |
| `TIMEOUT` | Operation timed out | Slow network share |
| `UNKNOWN` | Anything else | Unexpected OS errors |

## Where Errors Are Logged

1. **Console** — one warning line per error
2. **Log file** — `sweep.log`, append-only, includes category + path + message
3. **Database** — `errors` table, queryable after crawl

## Querying Errors After Crawl

```bash
# How many errors by category?
python3 -c "
import sqlite3
db = sqlite3.connect('sweep.db')
for row in db.execute('SELECT category, COUNT(*) FROM errors GROUP BY category ORDER BY COUNT(*) DESC'):
    print(f'{row[0]:20} {row[1]}')
"

# Show all permission errors
python3 -c "
import sqlite3
db = sqlite3.connect('sweep.db')
for row in db.execute('SELECT path FROM errors WHERE category=\"PERMISSION\" LIMIT 20'):
    print(row[0])
"
```
