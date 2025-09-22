# Integration Tests for Acumba Automation

This directory contains comprehensive integration tests for the Acumba Automation project, covering both API and scraping endpoints with safe data handling practices.

## 🚀 Quick Start

```bash
# Install test dependencies
fish -c "source .venv/bin/activate.fish; pip install pytest pytest-timeout"

# Run all integration tests
fish -c "source .venv/bin/activate.fish; pytest tests/integration/"

# Run only API tests
fish -c "source .venv/bin/activate.fish; pytest -m api"

# Run only scraping tests
fish -c "source .venv/bin/activate.fish; pytest -m scraping"

# Skip destructive tests (that create/delete data)
fish -c "source .venv/bin/activate.fish; pytest -m 'not destructive'"

# Skip slow tests
fish -c "source .venv/bin/activate.fish; pytest -m 'not slow'"
```

## 📁 Test Structure

```
tests/
├── conftest.py                           # Shared fixtures and configuration
├── pytest.ini                           # Pytest configuration
├── integration/
│   ├── test_api_suscriptores.py         # API subscriber endpoint tests
│   ├── test_api_campanias.py            # API campaign endpoint tests
│   ├── test_scraping_suscriptores.py    # Scraping subscriber tests
│   ├── test_scraping_campanias.py       # Scraping campaign tests
│   └── test_cleanup_manager.py          # Data cleanup and isolation tests
└── README.md                            # This file
```

## 🛡️ Safe Testing Practices

### Data Isolation
- **Unique Prefixes**: All test data uses timestamp-based prefixes (`TEST_YYYYMMDD_HHMMSS_`)
- **Automatic Cleanup**: Test data is automatically cleaned up after each test
- **Isolated Sessions**: Multiple test sessions don't interfere with each other

### Rate Limiting
- Built-in rate limiting respects API limits
- Configurable delays between API calls
- Separate tracking for different endpoints

### Test Categories
- **`@pytest.mark.integration`**: Integration tests requiring real services
- **`@pytest.mark.destructive`**: Tests that create/delete data (safe cleanup)
- **`@pytest.mark.slow`**: Tests that take longer to run
- **`@pytest.mark.api`**: API endpoint tests
- **`@pytest.mark.scraping`**: Web scraping tests

## 🔧 Configuration

### Prerequisites
1. Valid `config.yaml` with API credentials
2. Network access to Acumbamail services
3. Python virtual environment activated

### Environment Variables
```bash
# Optional: Override test timeouts
export PYTEST_TIMEOUT=3600  # 1 hour for very slow tests
```

## 📋 Test Coverage

### API Endpoints Tested

#### Suscriptores API (`test_api_suscriptores.py`)
- ✅ **Create/Delete List Lifecycle**: Complete CRUD operations
- ✅ **Subscriber CRUD Operations**: Add, update, delete subscribers
- ✅ **Batch Operations**: Bulk subscriber management
- ✅ **Search Operations**: Cross-list subscriber search
- ✅ **Field Management**: Custom fields and merge tags
- ✅ **List Statistics**: Comprehensive list analytics
- ✅ **Error Handling**: Invalid data and edge cases

#### Campanias API (`test_api_campanias.py`)
- ✅ **Campaign Listing**: All campaigns with summary/complete info
- ✅ **Campaign Details**: Basic and detailed campaign information
- ✅ **Campaign Analytics**: Openers, clickers, links, bounces
- ✅ **Date-based Statistics**: Campaign stats by date range
- ✅ **Data Validation**: Date format and range validation
- ✅ **Error Handling**: Invalid campaign IDs and edge cases

### Scraping Endpoints Tested

#### Suscriptores Scraping (`test_scraping_suscriptores.py`)
- ✅ **Scraper Initialization**: Configuration and setup
- ✅ **Filter Selection**: Mock and real filter operations
- ✅ **Table Extraction**: Data extraction from web tables
- ✅ **Navigation**: Page navigation and URL handling
- ✅ **Data Models**: Scraping data structure validation
- ✅ **Performance**: Large dataset simulation
- ✅ **Error Resilience**: Timeout and failure handling

#### Campanias Scraping (`test_scraping_campanias.py`)
- ✅ **Skeleton Implementation**: Framework testing
- ✅ **Non-openers Extraction**: Email list extraction (mocked)
- ✅ **Hard Bounces**: Detailed bounce information (mocked)
- ✅ **Extended Statistics**: Geographic and device stats (mocked)
- ✅ **Data Models**: Campaign scraping data structures
- ✅ **Performance**: Concurrent scraping simulation
- ✅ **Edge Cases**: Invalid campaigns and partial data

### Data Management (`test_cleanup_manager.py`)
- ✅ **Cleanup Lifecycle**: Complete cleanup verification
- ✅ **Data Isolation**: Multi-session isolation testing
- ✅ **Error Resilience**: Cleanup with invalid data
- ✅ **Batch Operations**: Efficient multi-item cleanup
- ✅ **Rate Limiting**: Rate limit helper functionality
- ✅ **Configuration**: Test setup and fixtures

## 🎯 Running Specific Tests

### By Category
```bash
# Only read-only tests (no data creation)
fish -c "source .venv/bin/activate.fish; pytest -m 'integration and not destructive'"

# Only fast tests
fish -c "source .venv/bin/activate.fish; pytest -m 'integration and not slow'"

# Only API tests
fish -c "source .venv/bin/activate.fish; pytest -m 'api'"

# Only scraping tests
fish -c "source .venv/bin/activate.fish; pytest -m 'scraping'"
```

### By Test File
```bash
# Test specific endpoint
fish -c "source .venv/bin/activate.fish; pytest tests/integration/test_api_suscriptores.py"

# Test specific class
fish -c "source .venv/bin/activate.fish; pytest tests/integration/test_api_suscriptores.py::TestSuscriptoresAPIIntegration"

# Test specific method
fish -c "source .venv/bin/activate.fish; pytest tests/integration/test_api_suscriptores.py::TestSuscriptoresAPIIntegration::test_create_and_delete_list_lifecycle"
```

### Verbose Output
```bash
# Detailed output with timing
fish -c "source .venv/bin/activate.fish; pytest -v --durations=10 tests/integration/"

# Show all output (including print statements)
fish -c "source .venv/bin/activate.fish; pytest -s tests/integration/"
```

## 🚨 Important Safety Notes

### Data Protection
- **NEVER run tests against production data**
- **All test data has unique prefixes and is auto-cleaned**
- **Tests only manipulate data they create**
- **Failed tests still trigger cleanup**

### Rate Limiting
- **Tests respect API rate limits automatically**
- **Large test suites may take significant time**
- **Parallel execution is limited to prevent API overload**

### Authentication
- **Tests require valid API credentials**
- **Configuration is loaded from `config.yaml`**
- **No credentials are stored in test code**

## 🐛 Troubleshooting

### Common Issues

#### Tests Skip with "No configuration file found"
```bash
# Ensure config.yaml exists and is valid
ls config.yaml
# Check configuration format
```

#### Rate Limit Errors
```bash
# Run tests with longer delays
fish -c "source .venv/bin/activate.fish; pytest --timeout=3600 -m 'not slow'"
```

#### Cleanup Failures
```bash
# Run cleanup test specifically
fish -c "source .venv/bin/activate.fish; pytest tests/integration/test_cleanup_manager.py::TestCleanupMechanisms::test_cleanup_resilience"
```

#### Browser/Scraping Issues
```bash
# Install playwright browsers
fish -c "source .venv/bin/activate.fish; playwright install"

# Run only mocked scraping tests
fish -c "source .venv/bin/activate.fish; pytest tests/integration/test_scraping_campanias.py -m 'not skipif'"
```

### Debug Mode
```bash
# Run with maximum verbosity and debug info
fish -c "source .venv/bin/activate.fish; pytest -vv -s --tb=long --log-cli-level=DEBUG tests/integration/"
```

## 📊 Performance Expectations

### Typical Test Duration
- **Individual API test**: 2-10 seconds
- **Individual scraping test**: 1-5 seconds (mocked)
- **Complete test suite**: 5-15 minutes
- **Destructive tests only**: 10-30 minutes

### Resource Usage
- **Memory**: ~100-500MB during execution
- **Network**: Moderate API calls (rate-limited)
- **Storage**: Minimal temporary files

## 🔄 Continuous Integration

### Recommended CI Configuration
```yaml
# Example CI step
- name: Run Integration Tests
  run: |
    source .venv/bin/activate.fish
    pytest tests/integration/ -m "integration and not slow" --timeout=1800
```

### Test Selection for CI
- **PR Tests**: `-m "integration and not destructive and not slow"`
- **Nightly Tests**: `-m "integration"`
- **Release Tests**: All integration tests with extended timeout

## 📚 Additional Resources

- **Main Documentation**: `CLAUDE.md`
- **API Documentation**: `src/api/`
- **Scraping Documentation**: `src/scraping/`
- **Configuration Guide**: `config.yaml.example`

## 🤝 Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py`
2. **Use appropriate markers**: `@pytest.mark.integration`, etc.
3. **Implement cleanup**: Use `test_data_manager` fixture
4. **Respect rate limits**: Use `rate_limit_helper` fixture
5. **Document test purpose**: Clear docstrings
6. **Test error cases**: Include negative testing