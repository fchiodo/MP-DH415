# Backtest databases

Drop here the SQLite databases produced by the MP-DH415-BT backtesting engine
(e.g. `my_database_2024.db`). They are served read-only by the API
(`/api/backtest/*`) and shown in the dashboard's **Backtest** page.

Discovery order (first directory wins on duplicate filenames):

1. `$BACKTEST_DB_DIR` (if set)
2. this folder (`<repo root>/backtest/`)
3. `../MP-DH415-BT/` (sibling project, local dev)

`.db` files are gitignored: on the server, copy them manually, e.g.

```bash
scp my_database_2024.db user@server:~/MP-DH415/backtest/
```
