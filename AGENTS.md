# Repository Guidelines

## Project Structure & Module Organization
- `src/`: Core modules (`autentificacion.py`, `crear_lista.py`, `listar_campanias.py`, `utils.py`, `logger.py`, `demo.py`).
- `app.py`: Entry point used for packaging with PyInstaller.
- `data/`: Runtime artifacts (logs, Excel inputs/outputs, session data). Treat as generated.
- `config.yaml`: Local settings (credentials, URLs, speed). Do not commit real secrets.
- Docs: `README.md`, `MANUAL_USUARIO.md`, `DISEÑO_TECNICO.md`.

## Build, Test, and Development Commands
**CRITICAL: This project uses fish shell. All Python/pip commands MUST be executed using fish with venv activation.**

- Create venv: `python -m venv .venv && source .venv/bin/activate.fish` (fish shell).
- Install deps: `fish -c "source .venv/bin/activate.fish; pip install -r requirements.txt"`.
- Install browsers (first run): `fish -c "source .venv/bin/activate.fish; python -m playwright install"`.
- Run locally: `fish -c "source .venv/bin/activate.fish; python src/demo.py"` (reads `config.yaml`, writes to `data/`).
- Lint: `fish -c "source .venv/bin/activate.fish; ruff check ."` Format: `fish -c "source .venv/bin/activate.fish; ruff format ."`.
- Build executable: `fish -c "source .venv/bin/activate.fish; pyinstaller --onefile --collect-all playwright app.py"`.

**For Claude Code agents: NEVER run Python commands directly. Always use the fish shell pattern above.**

## Coding Style & Naming Conventions
- Python 3.8+; 4‑space indentation; PEP 8 with Ruff.
- Names: `snake_case` for files/functions, `CapWords` for classes. Keep existing Spanish module/function names consistent.
- Type hints encouraged for public functions. Add short docstrings (purpose, params, returns).
- Use `src/logger.py` for logging; avoid `print` in library code.
- File paths via `pathlib`; write artifacts under `data/`.

## Testing Guidelines

### Integration Testing Framework (Comprehensive)
- **Location**: `tests/integration/` with complete API and scraping test coverage
- **Framework**: pytest with custom fixtures for safe data handling
- **Install**: `fish -c "source .venv/bin/activate.fish; pip install pytest pytest-timeout"`

### Test Categories & Safety Markers
- `@pytest.mark.integration`: Real service integration tests
- `@pytest.mark.destructive`: Tests that create/delete data (SAFE - auto-cleanup)
- `@pytest.mark.api`: API endpoint tests
- `@pytest.mark.scraping`: Web scraping tests (mostly mocked)
- `@pytest.mark.slow`: Long-running tests

### Running Tests (SAFE Commands)
```bash
# Recommended: Safe tests only (no data creation)
fish -c "source .venv/bin/activate.fish; pytest -m 'integration and not destructive' tests/integration/"

# API endpoint tests
fish -c "source .venv/bin/activate.fish; pytest -m api tests/integration/"

# Scraping tests (mocked)
fish -c "source .venv/bin/activate.fish; pytest -m scraping tests/integration/"

# All tests (includes destructive with auto-cleanup)
fish -c "source .venv/bin/activate.fish; pytest tests/integration/"

# Specific test file
fish -c "source .venv/bin/activate.fish; pytest tests/integration/test_api_suscriptores.py -v"
```

### Test Safety Mechanisms
- **Unique Prefixes**: All test data uses `TEST_YYYYMMDD_HHMMSS_` prefixes
- **Auto-Cleanup**: Automatic cleanup of test-created data (even on failures)
- **Data Isolation**: Tests only manipulate data they create
- **Rate Limiting**: Built-in API rate limiting to prevent overload
- **Production Safety**: IMPOSSIBLE to modify existing non-test data

### Test Documentation
- **Complete Guide**: `tests/README.md` - comprehensive testing documentation
- **Test Configuration**: `tests/conftest.py` - shared fixtures and safety mechanisms
- **Coverage**: 79 integration tests covering API and scraping endpoints

## Commit & Pull Request Guidelines
- Commits: imperative, present tense, concise (e.g., `add multiple sheet selection`). Group related changes.
- Before PR: run `fish -c "source .venv/bin/activate.fish; ruff check ."`, `fish -c "source .venv/bin/activate.fish; ruff format ."`, and a local run of `fish -c "source .venv/bin/activate.fish; python src/demo.py"`.
- PRs must include: summary, motivation, screenshots/logs for UI flows, steps to reproduce/verify, and linked issues.

## Playwright Automation Best Practices

### Modern Locator Strategy (2024-2025)
- **PRIORITY ORDER**: Use this hierarchy for element selection:
  1. `page.get_by_role("button", name="Text")` - Accessibility-based (highest priority)
  2. `page.get_by_text("Text")` - User-visible text
  3. `page.get_by_label("Label")` - Form labels
  4. `page.get_by_test_id("test-id")` - Test attributes
  5. `page.locator("css=selector")` - CSS/XPath (last resort)

### Element Interaction Patterns
- **Auto-waiting**: Playwright automatically waits for elements to be actionable. Avoid manual `time.sleep()`.
- **Safe interactions**: Use built-in methods that handle stability checks:
  ```python
  page.get_by_role("button", name="Submit").click()  # Auto-waits for visible, enabled, stable
  page.get_by_label("Email").fill("text")  # Auto-clears and fills
  ```
- **Error handling**: Use try/except with Playwright's `TimeoutError`:
  ```python
  from playwright.sync_api import TimeoutError as PWTimeoutError
  try:
      page.get_by_text("Loading...").wait_for(state="hidden", timeout=10000)
  except PWTimeoutError:
      logger.warning("Element didn't disappear within timeout")
  ```

### Performance & Reliability
- **Navigation**: Use `wait_until="domcontentloaded"` for faster page loads when full network idle isn't needed
- **Context isolation**: Always use browser contexts for session management and state persistence
- **Timeouts**: Configure reasonable timeouts via `utils.get_timeouts()` - don't hardcode values
- **Page state**: Use `page.wait_for_load_state()` instead of arbitrary waits

### Current Project Integration
- Use `crear_contexto_navegador()` for consistent browser setup with anti-detection features
- Leverage `storage_state_path()` for session persistence across runs
- Follow existing patterns in `src/autentificacion.py` for login flows
- Utilize `src/logger.py` for comprehensive operation timing and debugging

### Deprecated Patterns to Avoid
- CSS selectors like `page.click(".class-name")` → Use role-based locators
- Manual wait strategies with `time.sleep()` → Use Playwright's auto-waiting
- Direct element attribute access → Use Playwright's assertion methods
- Complex XPath expressions → Use semantic locators when possible

### Reference Documentation
- Complete best practices guide: `DOCS/playwright-python-best-practices.md`
- Official docs: https://playwright.dev/python/

## Security & Configuration Tips
- Never commit real credentials; use placeholders in `config.yaml`. Consider a `config.example.yaml` for sharing.
- Treat `data/` outputs and logs as ephemeral; avoid committing sensitive artifacts.
