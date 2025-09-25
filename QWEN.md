# QWEN.md

This file provides guidance to Qwen AI (Qwen Code) when working with code in this repository.

## Project Overview

This is a Python automation tool for email marketing campaign reporting from Acumbamail. The application provides both a GUI (app.py) and CLI interface for automating campaign data extraction and subscriber management.

## Key Commands

### Development Environment
```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux (bash/zsh)
source .venv/bin/activate.fish  # macOS/Linux (fish shell)
.venv\\Scripts\\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for automation)
playwright install
```

**IMPORTANT for Qwen Code:**
- This project uses fish shell as the primary shell environment
- ALWAYS use fish shell commands when running Python/pip commands
- Example: `fish -c "source .venv/bin/activate.fish; python app.py"`
- All Python commands should be executed within the virtual environment using fish

### Code Quality
```bash
# Format and lint code (use fish shell with venv)
fish -c "source .venv/bin/activate.fish; ruff check ."
fish -c "source .venv/bin/activate.fish; ruff format ."
```

### Running the Application
```bash
# GUI Application (use fish shell with venv)
fish -c "source .venv/bin/activate.fish; python app.py"

# CLI - Campaign listing (run from project root)
fish -c "source .venv/bin/activate.fish; python -m src.listar_campanias"

# CLI - Subscriber extraction (run from project root)
fish -c "source .venv/bin/activate.fish; python -m src.demo"
```

### Build Executable
```bash
# Create standalone executable with Playwright (use fish shell with venv)
fish -c "source .venv/bin/activate.fish; pyinstaller --onefile --collect-all playwright app.py"
```

### Integration Testing
```bash
# Install test dependencies
fish -c "source .venv/bin/activate.fish; pip install pytest pytest-timeout"

# Run safe tests only (recommended for CI/development)
fish -c "source .venv/bin/activate.fish; pytest -m 'integration and not destructive' tests/integration/"

# Run API endpoint tests
fish -c "source .venv/bin/activate.fish; pytest -m api tests/integration/"

# Run scraping tests (mostly mocked)
fish -c "source .venv/bin/activate.fish; pytest -m scraping tests/integration/"

# Run all tests (includes destructive tests - SAFE with auto-cleanup)
fish -c "source .venv/bin/activate.fish; pytest tests/integration/"

# Test specific functionality
fish -c "source .venv/bin/activate.fish; pytest tests/integration/test_api_suscriptores.py -v"
```

**IMPORTANT for Integration Tests:**
- All tests use unique prefixes (TEST_YYYYMMDD_HHMMSS_) for safe data isolation
- Destructive tests automatically clean up their own data
- Tests NEVER modify existing production data
- Rate limiting is automatically applied to respect API limits
- See `tests/README.md` for complete testing documentation

## Architecture

### Core Modules
- **app.py**: Main GUI application using tkinter with threaded operations
- **src/demo.py**: Main automation script for subscriber data extraction
- **src/listar_campanias.py**: Campaign listing automation
- **src/crear_lista.py**: Subscriber list creation with Excel sheet selection
- **src/autentificacion.py**: Login automation for Acumbamail
- **src/utils.py**: Shared utilities for browser automation, file handling, and configuration
- **src/tipo_campo.py**: Field type definitions for form automation

### Key Components

**Browser Automation Framework:**
- Uses Playwright for web automation
- Session persistence via storage_state_path() in data/datos_sesion.json
- Browser configuration in src/utils.py with custom user agent
- Browsers stored in ms-playwright/ directory for portable builds

**Performance Logging System:**
- Comprehensive timing and performance monitoring via src/logger.py
- Automatic timing for all major operations (login, navigation, data extraction)
- Daily log files stored in data/automation_YYYYMMDD.log
- Real-time performance reports with bottleneck identification
- Browser action logging, file operations tracking, and error reporting

**Data Flow:**
1. Configuration loaded from config.yaml (credentials, URLs)
2. Search terms loaded from data/Busqueda.xlsx
3. Automated login and navigation through Acumbamail interface
4. Campaign data extraction and Excel report generation
5. Results saved to data/informes_*.xlsx files

**Threading Model:**
- GUI operations run in main thread
- Browser automation runs in worker threads
- Progress notifications via root.after() for thread-safe GUI updates

### File Structure
```
├── app.py                 # Main GUI application
├── src/
│   ├── demo.py           # Main automation script
│   ├── listar_campanias.py  # Campaign listing
│   ├── crear_lista.py    # List creation
│   ├── autentificacion.py   # Login automation
│   ├── utils.py          # Shared utilities
│   ├── logger.py         # Performance logging system
│   └── tipo_campo.py     # Field definitions
├── data/                 # Excel files, session data, and logs
├── config.yaml           # Application configuration
└── ms-playwright/        # Playwright browser binaries
```

### Configuration
- **config.yaml**: Contains URL endpoints, credentials, and browser settings
- **data/Busqueda.xlsx**: Campaign search terms with columns: Buscar, Nombre, Tipo, Fecha envío, Listas, Emails, Abiertos, Clics
- **data/Lista_envio.xlsx**: Subscriber email lists for upload
- Session state automatically persisted for authentication

### Modern Playwright Automation Patterns (2024-2025)

**CRITICAL: Always follow modern Playwright best practices. See DOCS/playwright-python-best-practices.md for complete guidelines.**

**Element Selection Priority (MUST FOLLOW):**
1. **Role-based locators** (highest priority): `page.get_by_role("button", name="Text")`
2. **Text-based locators**: `page.get_by_text("Text")`
3. **Label-based locators**: `page.get_by_label("Label")`
4. **Test ID locators**: `page.get_by_test_id("test-id")`
5. **CSS/XPath selectors** (last resort): `page.locator("css=selector")`

**Auto-waiting Interactions:**
- Use Playwright's built-in auto-waiting instead of manual timeouts
- Example: `page.get_by_role("button", name="Submit").click()` automatically waits for element to be visible, enabled, and stable
- Avoid `time.sleep()` - use `page.wait_for_load_state()` or element waiting methods

**Current Implementation Guidelines:**
- Migrate legacy CSS selectors to role-based locators when making changes
- Use `crear_contexto_navegador()` for consistent browser setup with anti-detection
- Leverage session persistence via `storage_state_path()` for authentication
- Follow timeout configuration via `utils.get_timeouts()` instead of hardcoded values
- Utilize comprehensive logging via `src/logger.py` for operation timing

**Deprecated Legacy Patterns (to be migrated):**
- `page.click("css-selector")` → `page.get_by_role("button", name="Text").click()`
- `page.locator("xpath")` → Use semantic locators when possible
- Manual wait strategies → Use Playwright's auto-waiting features
- Direct element attribute access → Use Playwright's assertion methods

### Performance Monitoring & Optimization
The application includes comprehensive logging and timing to help optimize performance:

**Logging Features:**
- Automatic timing of all major operations (login, navigation, data extraction, file operations)
- Real-time performance monitoring with bottleneck identification
- Browser action logging with context and timing information
- Progress tracking for long-running operations (pagination, data extraction)
- Error tracking with context and operation details

**Log Output:**
- Console output with timestamped, categorized messages using emojis for easy identification
- Daily log files stored in `data/automation_YYYYMMDD.log`
- Performance reports showing slowest/fastest operations and total execution time

**Usage Example:**
```python
from src.logger import get_logger

logger = get_logger()
logger.start_timer("my_operation")
# ... your code ...
logger.end_timer("my_operation", "Additional context info")
logger.print_performance_report()  # At end of process
```

**Automatic Integration:**
All core modules (demo.py, utils.py, autentificacion.py) automatically include performance logging. The system provides detailed timing for:
- Configuration loading and validation
- Browser setup and navigation
- Authentication processes
- Campaign searching and data extraction
- Pagination and page processing
- Excel file generation and saving

**Debugging Tools:**
For troubleshooting process hang-ups or performance issues:

1. **Debug Mode Script:**
   ```bash
   python debug_script.py
   ```
   Runs the main process with extensive logging and heartbeat monitoring

2. **Real-time Log Monitor:**
   ```bash
   python monitor_logs.py
   ```
   Monitors log files in real-time to detect where processes get stuck

3. **Log Analysis:**
   - Look for `📍 CHECKPOINT` entries to see last successful operation
   - `💓 HEARTBEAT` entries show the process is still alive
   - `❌ ERROR` entries highlight failures
   - Time gaps between log entries indicate bottlenecks

**Common Hang-up Points:**
- Browser element location (selector timeouts)
- Page navigation waiting for networkidle
- Data extraction from large paginated results
- Element interaction (clicking, filling forms)

## Playwright Documentation & Best Practices Reference

**IMPORTANT: Always consult modern Playwright documentation before implementing browser automation:**

1. **Primary Reference**: `DOCS/playwright-python-best-practices.md` - Comprehensive guide with 2024-2025 patterns
2. **Official Documentation**: https://playwright.dev/python/
3. **Project Guidelines**: `AGENTS.md` contains Playwright best practices section

**When working with Playwright automation:**
- **ALWAYS** start by consulting the documentation in `DOCS/playwright-python-best-practices.md`
- Use modern locator strategies (role-based, text-based) over legacy CSS selectors
- Follow the element selection priority hierarchy defined in the documentation
- Implement auto-waiting patterns instead of manual timing
- Use browser contexts for session isolation and persistence
- Apply performance optimization techniques for large-scale automation

**Code Review Checklist:**
- [ ] Uses role-based locators (`get_by_role`) where possible
- [ ] Avoids CSS selectors unless absolutely necessary
- [ ] Implements auto-waiting instead of `time.sleep()`
- [ ] Uses browser context for session management
- [ ] Includes proper error handling with Playwright exceptions
- [ ] Follows timeout configuration via `utils.get_timeouts()`
- [ ] Utilizes comprehensive logging via `src/logger.py`

**Migration Strategy:**
When updating existing automation code, prioritize migrating:
1. CSS selectors to role-based locators
2. Manual waits to auto-waiting patterns
3. Direct element access to Playwright assertions
4. Hardcoded timeouts to configurable values

## Using the MCP Browser for Verification

When working with this project, you may need to verify certain aspects of the Acumbamail platform or web application. For this, use the mcp browser tool to access and interact with web resources. This is especially helpful for:

- Verifying Acumbamail interface changes
- Understanding the current structure of web elements
- Testing selector strategies before implementing automation
- Checking if web elements behave as expected
- Validating changes to important modules after modifications
- Verifying Excel data mappings and structures match the Acumbamail platform

When using the browser tool, always respect the platform's terms of service and rate limiting to avoid being blocked.

## Validation Requirements for Important Files

When modifying important modules (the main application files), you must validate changes using the MCP browser to ensure functionality remains correct:

### Core Modules Requiring Validation
The following modules are considered important and require MCP browser validation after modification:
- **app.py**: Main GUI application
- **src/demo.py**: Main automation script for subscriber data extraction
- **src/listar_campanias.py**: Campaign listing automation
- **src/crear_lista.py**: Subscriber list creation with Excel sheet selection
- **src/autentificacion.py**: Login automation for Acumbamail
- **src/utils.py**: Shared utilities for browser automation, file handling, and configuration

After modifying any of these files, always use the MCP browser to:
1. Verify that login functionality still works correctly
2. Check that campaign data extraction works as expected
3. Ensure that Excel data generation matches Acumbamail platform data
4. Validate that browser automation flows function properly

### Excel Data Validation
When working with Excel files in the data directory (particularly Busqueda.xlsx and Lista_envio.xlsx), always cross-reference with the actual Acumbamail platform using the MCP browser to ensure:
- Column mappings are correct
- Data formats match what the platform expects
- Campaign names and search terms are valid
- Email formats and list structures are properly formatted
- Extracted data matches what's shown in the Acumbamail interface
