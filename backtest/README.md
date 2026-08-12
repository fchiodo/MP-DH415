# Backtest databases

SQLite databases shown in the dashboard's **Backtest** page, served read-only
by the API (`/api/backtest/*`).

Two kinds of databases are discovered:

1. **Per-year working DBs** — written by `backend/backtest_runner.py` (the
   "Run Backtest" button): each run works in `years/<year>/my_database.db`
   and shows up as the `<year>` tab. Created automatically with the full
   25-column schema; trades appear here live while the run progresses.
2. **Static archives** — drop legacy `.db` files from the MP-DH415-BT project
   in this folder (e.g. `my_database_2024.db`) or keep them in the sibling
   `../MP-DH415-BT/` project.

Discovery order (first source wins on duplicate names):

1. `$BACKTEST_DB_DIR` (if set)
2. `years/<year>/my_database.db` (exposed as `my_database_<year>.db`)
3. this folder (`<repo root>/backtest/`)
4. `../MP-DH415-BT/` (sibling project, local dev)

`.db` files are gitignored. `engine_output.log` is the raw engine output of
the latest run (truncated at each run start).
