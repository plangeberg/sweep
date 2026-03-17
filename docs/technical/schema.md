# Sweep — Database Schema

## Tables

### `metadata`
Project-level key-value store.

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT PK | Setting name |
| `value` | TEXT | Setting value |

Keys: `schema_version`, `created_at`

### `folders`
One record per directory found during crawl.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `path` | TEXT UNIQUE | Full directory path |
| `name` | TEXT | Directory name |
| `parent_path` | TEXT | Parent directory path |
| `modified_at` | TEXT | Last modified (ISO 8601 UTC) |
| `created_at` | TEXT | Created (ISO 8601 UTC, NULL if unavailable) |
| `discovered_at` | TEXT | When crawler found it |

### `files`
One record per file found during crawl.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `folder_id` | INTEGER FK | References folders(id) |
| `path` | TEXT UNIQUE | Full file path |
| `name` | TEXT | Filename |
| `extension` | TEXT | Lowercase with dot (`.pdf`, `.docx`) |
| `size_bytes` | INTEGER | File size |
| `modified_at` | TEXT | Last modified (ISO 8601 UTC) |
| `created_at` | TEXT | Created (ISO 8601 UTC, NULL if unavailable) |
| `content_hash` | TEXT | MD5 hash (NULL if hashing disabled) |
| `discovered_at` | TEXT | When crawler found it |

### `crawl_state`
Resume tracking — one record per directory.

| Column | Type | Description |
|--------|------|-------------|
| `path` | TEXT PK | Directory path |
| `status` | TEXT | `pending`, `in_progress`, `complete`, `error` |
| `file_count` | INTEGER | Files found in this directory |
| `error_count` | INTEGER | Errors in this directory |
| `updated_at` | TEXT | Last state change |

### `errors`
Queryable error log.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `path` | TEXT | Path that caused error |
| `category` | TEXT | PERMISSION, SYMLINK, LOCKED, NETWORK, PATH_TOO_LONG, ENCODING, TIMEOUT, UNKNOWN |
| `message` | TEXT | Error description |
| `occurred_at` | TEXT | When it happened |

## Indexes

- `idx_files_extension` — fast extension queries
- `idx_files_folder_id` — fast folder→files joins
- `idx_files_modified` — fast "recently modified" queries
- `idx_folders_parent` — fast tree navigation
- `idx_crawl_state_status` — fast resume lookup

## Pragmas

- `journal_mode=WAL` — crash safety, concurrent reads
- `synchronous=NORMAL` — balanced durability/performance
- `foreign_keys=ON` — referential integrity
