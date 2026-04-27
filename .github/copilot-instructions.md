# Project Guidelines

## Architecture
- Flask backend (`backend/`) with Firebase integration and CSV-based demo mode
- Static frontend (`frontend/`) served by Flask or Firebase Hosting
- Self-contained `livedemo/` folder for customer demos
- Data files in `data/` and `qr_codes/` (CSV format, no xlsx)

## Build and Test
```bash
pip install -r backend/requirements.txt -r requirements-test.txt
pytest --cov=backend --cov-report=term-missing -v
```

## Post-Response Workflow
After EVERY code change response, the agent MUST run these steps in order:
1. **Run tests**: `pytest backend/tests tests -v --tb=short`
2. **Git commit**: `git add -A && git commit -m "<descriptive message>"`
3. **Git push**: `git push`
4. **Verify CI**: Check that GitHub Actions CI passes
5. **Deploy** (if frontend changed): `firebase deploy --only hosting`

Never skip steps. If tests fail, fix before committing. If CI fails, fix immediately.

## Conventions
- All data files use CSV (never xlsx/openpyxl)
- Use `BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` for absolute paths
- Demo mode runs without Firebase (no serviceAccountKey.json required)
- Tests use `monkeypatch.setenv('K_SERVICE', 'test')` to avoid overwriting real data files
- Frontend uses `textContent`/`createElement` (never `innerHTML`) to prevent XSS
