# Repository Guidelines

## Project Structure & Module Organization
- `src/`: Core modules (`autentificacion.py`, `crear_lista.py`, `listar_campanias.py`, `utils.py`, `logger.py`, `demo.py`).
- `app.py`: Entry point used for packaging with PyInstaller.
- `data/`: Runtime artifacts (logs, Excel inputs/outputs, session data). Treat as generated.
- `config.yaml`: Local settings (credentials, URLs, speed). Do not commit real secrets.
- Docs: `README.md`, `MANUAL_USUARIO.md`, `DISEÑO_TECNICO.md`.

## Build, Test, and Development Commands
- Create venv: `python -m venv .venv && source .venv/bin/activate`.
- Install deps: `pip install -r requirements.txt`.
- Install browsers (first run): `python -m playwright install`.
- Run locally: `python src/demo.py` (reads `config.yaml`, writes to `data/`).
- Lint: `ruff check .`  Format: `ruff format .`.
- Build executable: `pyinstaller --onefile --collect-all playwright app.py`.

## Coding Style & Naming Conventions
- Python 3.8+; 4‑space indentation; PEP 8 with Ruff.
- Names: `snake_case` for files/functions, `CapWords` for classes. Keep existing Spanish module/function names consistent.
- Type hints encouraged for public functions. Add short docstrings (purpose, params, returns).
- Use `src/logger.py` for logging; avoid `print` in library code.
- File paths via `pathlib`; write artifacts under `data/`.

## Testing Guidelines
- Framework: pytest (add to dev env if needed). Structure tests in `tests/` with `test_*.py`.
- Run: `python -m pytest -q` (optionally `-k <pattern>`). Use markers `@pytest.mark.integration` for Playwright flows.
- Prefer unit tests for `utils.py` and pure functions; keep integration tests stable with realistic waits/timeouts.

## Commit & Pull Request Guidelines
- Commits: imperative, present tense, concise (e.g., `add multiple sheet selection`). Group related changes.
- Before PR: run `ruff check .`, `ruff format .`, and a local run of `python src/demo.py`.
- PRs must include: summary, motivation, screenshots/logs for UI flows, steps to reproduce/verify, and linked issues.

## Security & Configuration Tips
- Never commit real credentials; use placeholders in `config.yaml`. Consider a `config.example.yaml` for sharing.
- Treat `data/` outputs and logs as ephemeral; avoid committing sensitive artifacts.
