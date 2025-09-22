# Playwright Python Best Practices & Modern Usage Guide

## Table of Contents
1. [Installation & Setup](#installation--setup)
2. [Core API Patterns](#core-api-patterns)
3. [Modern Locator Strategies](#modern-locator-strategies)
4. [Browser Context Best Practices](#browser-context-best-practices)
5. [Element Interaction Patterns](#element-interaction-patterns)
6. [Error Handling & Reliability](#error-handling--reliability)
7. [Performance Optimization](#performance-optimization)
8. [Migration from Selenium](#migration-from-selenium)

## Installation & Setup

### Required Installation
```bash
# Install Playwright for Python
pip install playwright

# Install browsers (required for automation)
playwright install

# For testing with pytest
pip install pytest-playwright
```

### System Requirements
- Python 3.8+
- Windows 10+, macOS 14+, Debian/Ubuntu

## Core API Patterns

### Modern Synchronous Pattern (Recommended for Scripts)
```python
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as playwright:
        # Launch browser
        browser = playwright.chromium.launch(headless=False)

        # Create context for session isolation
        context = browser.new_context()

        # Create page
        page = context.new_page()

        # Navigate and interact
        page.goto("https://example.com")

        # Clean up
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
```

### Asynchronous Pattern (For High Performance)
```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://example.com")

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Modern Locator Strategies

### Recommended Locator Priority (2024-2025)

1. **Role-based Locators (Highest Priority)**
```python
# Buttons
page.get_by_role("button", name="Sign in").click()
page.get_by_role("button", name=re.compile("submit", re.IGNORECASE)).click()

# Links
page.get_by_role("link", name="Home").click()

# Form inputs
page.get_by_role("textbox", name="Email").fill("user@example.com")
page.get_by_role("combobox", name="Country").select_option("Spain")
```

2. **Text-based Locators**
```python
# Exact text match
page.get_by_text("Sign in").click()

# Partial text match
page.get_by_text("Welcome", exact=False).click()

# Regular expression
page.get_by_text(re.compile(r"Sign [iI]n")).click()
```

3. **Label-based Locators (Forms)**
```python
page.get_by_label("Email address").fill("user@example.com")
page.get_by_label("Password").fill("securepassword")
```

4. **Test ID Locators (When Above Not Available)**
```python
page.get_by_test_id("login-button").click()
```

5. **CSS/XPath (Last Resort)**
```python
# CSS selector
page.locator("css=.login-form button[type='submit']").click()

# XPath
page.locator("xpath=//button[contains(text(), 'Submit')]").click()
```

### Advanced Locator Techniques

**Filtering and Chaining**
```python
# Filter by text content
page.get_by_role("listitem").filter(has_text="Premium").click()

# Filter by child elements
page.get_by_role("article").filter(has=page.get_by_role("button", name="Subscribe"))

# Chaining locators
page.get_by_role("navigation").get_by_role("link", name="Products").click()
```

**Multiple Elements**
```python
# Get all matching elements
all_buttons = page.get_by_role("button").all()
for button in all_buttons:
    print(button.text_content())

# Get specific element by index
first_button = page.get_by_role("button").first
last_button = page.get_by_role("button").last
second_button = page.get_by_role("button").nth(1)
```

## Browser Context Best Practices

### Session Persistence
```python
# Save authentication state
context = browser.new_context()
page = context.new_page()

# Perform login
page.goto("https://example.com/login")
page.get_by_label("Email").fill("user@example.com")
page.get_by_label("Password").fill("password")
page.get_by_role("button", name="Sign in").click()

# Save the authentication state
context.storage_state(path="auth.json")

# Reuse authentication state
context = browser.new_context(storage_state="auth.json")
```

### Device Emulation
```python
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        # Use predefined device
        context = browser.new_context(**playwright.devices["iPhone 13"])

        # Custom viewport
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Custom User Agent String"
        )
```

### Network Interception
```python
def handle_response(response):
    if "api/data" in response.url:
        print(f"API response: {response.status}")

page.on("response", handle_response)
page.goto("https://example.com")
```

## Element Interaction Patterns

### Auto-waiting Actions (No Manual Waits Needed)
```python
# Playwright automatically waits for elements to be actionable
page.get_by_role("button").click()  # Waits for visible, enabled, stable
page.get_by_label("Email").fill("text")  # Waits for visible, enabled
page.get_by_role("checkbox").check()  # Waits for visible, enabled
```

### Explicit Waiting (When Needed)
```python
# Wait for element to appear
page.get_by_text("Loading...").wait_for(state="hidden")
page.get_by_role("button", name="Submit").wait_for(state="visible")

# Wait for network activity
with page.expect_response("**/api/data") as response_info:
    page.get_by_role("button", name="Load Data").click()
response = response_info.value
```

### File Operations
```python
# File uploads
page.get_by_label("Upload file").set_input_files("path/to/file.pdf")

# Multiple files
page.get_by_label("Upload files").set_input_files([
    "file1.pdf",
    "file2.jpg"
])

# File downloads
with page.expect_download() as download_info:
    page.get_by_role("link", name="Download").click()
download = download_info.value
download.save_as("downloaded_file.pdf")
```

## Error Handling & Reliability

### Robust Error Handling
```python
from playwright.sync_api import TimeoutError, Error

def safe_click(page, locator_text, timeout=30000):
    try:
        page.get_by_text(locator_text).click(timeout=timeout)
        return True
    except TimeoutError:
        print(f"Element '{locator_text}' not found within {timeout}ms")
        return False
    except Error as e:
        print(f"Playwright error: {e}")
        return False
```

### Conditional Logic
```python
# Check if element exists
if page.get_by_text("Cookie banner").is_visible():
    page.get_by_role("button", name="Accept").click()

# Multiple possible outcomes
try:
    page.get_by_role("button", name="Submit").click(timeout=5000)
except TimeoutError:
    # Alternative path
    page.get_by_role("button", name="Send").click()
```

### Page State Assertions
```python
from playwright.sync_api import expect

# Modern assertions with auto-waiting
expect(page).to_have_title(re.compile("Dashboard"))
expect(page.get_by_role("button", name="Submit")).to_be_enabled()
expect(page.get_by_text("Success")).to_be_visible()
```

## Performance Optimization

### Efficient Page Navigation
```python
# Wait for network idle (all requests finished)
page.goto("https://example.com", wait_until="networkidle")

# Wait only for DOM content loaded (faster)
page.goto("https://example.com", wait_until="domcontentloaded")

# Disable images and CSS for faster loading (data extraction)
context = browser.new_context(
    bypass_csp=True,
    java_script_enabled=True,
    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
)
```

### Resource Blocking
```python
def block_images(route):
    if route.request.resource_type == "image":
        route.abort()
    else:
        route.continue_()

# Block unnecessary resources
page.route("**/*", block_images)
page.goto("https://example.com")
```

### Parallel Execution
```python
import asyncio
from playwright.async_api import async_playwright

async def process_page(page, url):
    await page.goto(url)
    title = await page.title()
    return title

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()

        # Create multiple pages for parallel processing
        pages = [await browser.new_page() for _ in range(3)]
        urls = ["https://site1.com", "https://site2.com", "https://site3.com"]

        # Process pages in parallel
        tasks = [process_page(page, url) for page, url in zip(pages, urls)]
        results = await asyncio.gather(*tasks)

        await browser.close()
        return results
```

## Migration from Selenium

### Common Pattern Migrations

**Element Finding**
```python
# Old Selenium way
element = driver.find_element(By.CSS_SELECTOR, ".login-button")
element.click()

# New Playwright way
page.get_by_role("button", name="Login").click()
```

**Waiting**
```python
# Old Selenium way
wait = WebDriverWait(driver, 10)
element = wait.until(EC.element_to_be_clickable((By.ID, "submit")))

# New Playwright way (automatic)
page.get_by_role("button", name="Submit").click()  # Auto-waits
```

**Form Handling**
```python
# Old Selenium way
email_field = driver.find_element(By.NAME, "email")
email_field.clear()
email_field.send_keys("user@example.com")

# New Playwright way
page.get_by_label("Email").fill("user@example.com")  # Automatically clears
```

## Modern Anti-Detection Techniques

### Stealth Configuration
```python
def create_stealth_context(browser):
    return browser.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none"
        },
        java_script_enabled=True,
        bypass_csp=True
    )
```

### Human-like Interactions
```python
import random
import time

def human_like_fill(page, locator, text):
    """Fill text with human-like typing speed"""
    page.get_by_label(locator).click()

    for char in text:
        page.keyboard.type(char)
        # Random delay between keystrokes
        time.sleep(random.uniform(0.05, 0.15))

def human_like_click(page, locator):
    """Click with slight delay and movement"""
    element = page.get_by_role("button", name=locator)
    element.hover()  # Hover first
    time.sleep(random.uniform(0.1, 0.3))  # Brief pause
    element.click()
```

## Key Differences from Legacy Automation

1. **Auto-waiting**: No need for explicit waits in most cases
2. **Browser contexts**: Better isolation and session management
3. **Modern locators**: Focus on user-facing attributes
4. **Built-in assertions**: Automatic retry and waiting
5. **Cross-browser**: Same API works across all browsers
6. **Performance**: Faster execution and more reliable
7. **Developer tools**: Built-in debugging and tracing capabilities

## Debugging Tools

### Playwright Inspector
```bash
# Run script with inspector
PWDEBUG=1 python your_script.py

# Or in code
page.pause()  # Pauses execution and opens inspector
```

### Trace Viewer
```python
# Start tracing
context.tracing.start(screenshots=True, snapshots=True)

# Your automation code here

# Stop tracing and save
context.tracing.stop(path="trace.zip")

# View trace: playwright show-trace trace.zip
```

This guide represents the modern, best-practice approach to Playwright automation in Python as of 2024-2025. Focus on role-based locators, automatic waiting, and browser contexts for the most reliable and maintainable automation scripts.