# Raw data

Append-only. Files here are evidence: add new ones, never modify or delete existing ones (the guard enforces it).

| File | What it is | Produced by |
|---|---|---|
| `weekly_events.csv` | Synthetic asset-week table: `week_start`, `asset_id`, `line`, `observed`, `events`, `downtime_min`. 240 assets × 104 weeks | [generate_data.py](../../examples/weekly_risk/generate_data.py), seed 20240101 |

After adding a file, run `make manifest` to register its SHA-256 in `MANIFEST.sha256`; `make check` verifies every hash.
