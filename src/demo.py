from playwright.sync_api import sync_playwright
def main():
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=False) # headless=False para ver
		context = browser.new_context()
		page = context.new_page()
		page.goto("https://example.com")
		print("Título:", page.title())
		page.screenshot(path="data/example.png", full_page=True)
		browser.close()
if __name__ == "__main__":
	main()