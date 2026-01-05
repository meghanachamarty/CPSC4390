# login_once.py
from playwright.sync_api import sync_playwright

CANVAS_BASE = "https://yale.instructure.com/"  # <-- change if your Canvas host is different

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(f"{CANVAS_BASE}/")   # or /login if your school uses a specific path
    print("\nLog in to Canvas in the opened window, then return here and press Enter…")
    input()
    ctx.storage_state(path="storage_state.json")
    browser.close()
    print("Saved session to storage_state.json")
