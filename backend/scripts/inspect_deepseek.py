"""
DOM inspector for DeepSeek login page.

Run with: python scripts/inspect_deepseek.py
Launches a headed browser and captures DOM details for login flow debugging.
"""
import asyncio
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def inspect():
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    page = await browser.new_page(viewport={"width": 1280, "height": 800})

    print("=" * 60)
    print("Step 1: Navigate to https://chat.deepseek.com")
    print("=" * 60)
    await page.goto("https://chat.deepseek.com", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)

    current_url = page.url
    print(f"Current URL: {current_url}")
    print(f"Title: {await page.title()}")

    # Take screenshot
    await page.screenshot(path="debug_deepseek_1_homepage.png")
    print("Screenshot saved: debug_deepseek_1_homepage.png")

    # Check if we're on login page already
    if "/login" in current_url or "/sign" in current_url:
        print(">>> Already on login page!")
    else:
        print(">>> Not on login page, looking for login button...")

    # Dump all interactive elements
    print("\n--- All buttons and links ---")
    elements = await page.evaluate("""
        () => {
            const results = [];
            for (const el of document.querySelectorAll('button, a, [role="button"]')) {
                const text = (el.textContent || '').trim().substring(0, 80);
                const tag = el.tagName;
                const href = el.getAttribute('href') || '';
                const cls = el.className || '';
                if (text || href) {
                    results.push({tag, text, href, class: typeof cls === 'string' ? cls.substring(0, 100) : ''});
                }
            }
            return results;
        }
    """)
    for el in elements:
        print(f"  <{el['tag']}> text='{el['text']}' href='{el['href']}' class='{el['class']}'")

    # Navigate to login page directly
    print("\n" + "=" * 60)
    print("Step 2: Navigate to login page directly")
    print("=" * 60)

    # Try direct login URL
    login_urls = [
        "https://chat.deepseek.com/sign_in",
        "https://chat.deepseek.com/login",
    ]

    for login_url in login_urls:
        print(f"Trying: {login_url}")
        try:
            await page.goto(login_url, wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(3)
            print(f"  Result URL: {page.url}")
            if "/sign" in page.url or "/login" in page.url:
                print("  >>> Found login page!")
                break
        except Exception as e:
            print(f"  Error: {e}")

    await asyncio.sleep(3)
    await page.screenshot(path="debug_deepseek_2_login_page.png")
    print("Screenshot saved: debug_deepseek_2_login_page.png")

    # Dump all inputs on login page
    print("\n--- All input elements ---")
    inputs = await page.evaluate("""
        () => {
            const results = [];
            for (const el of document.querySelectorAll('input, textarea')) {
                results.push({
                    tag: el.tagName,
                    type: el.type || '',
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    id: el.id || '',
                    class: (el.className || '').substring(0, 100),
                    value: el.value || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                });
            }
            return results;
        }
    """)
    for inp in inputs:
        print(f"  <{inp['tag']}> type='{inp['type']}' name='{inp['name']}' placeholder='{inp['placeholder']}' id='{inp['id']}' aria-label='{inp['ariaLabel']}'")

    # Dump all buttons
    print("\n--- All buttons on login page ---")
    buttons = await page.evaluate("""
        () => {
            const results = [];
            for (const el of document.querySelectorAll('button, [role="button"], a.btn, input[type="submit"]')) {
                results.push({
                    tag: el.tagName,
                    text: (el.textContent || '').trim().substring(0, 80),
                    type: el.type || '',
                    disabled: el.disabled,
                    class: (el.className || '').substring(0, 150),
                });
            }
            return results;
        }
    """)
    for btn in buttons:
        print(f"  <{btn['tag']}> text='{btn['text']}' type='{btn['type']}' disabled={btn['disabled']} class='{btn['class']}'")

    # Look for tabs (email vs phone login)
    print("\n--- Tab/Switch elements (email vs phone) ---")
    tabs = await page.evaluate("""
        () => {
            const results = [];
            const keywords = ['手机', '邮箱', 'phone', 'email', 'SMS', '短信', 'mobile', '密码'];
            for (const el of document.querySelectorAll('div, span, button, a, label, li, [role="tab"]')) {
                const t = (el.textContent || '').trim();
                if (t.length > 50) continue;
                if (keywords.some(kw => t.toLowerCase().includes(kw.toLowerCase()))) {
                    results.push({
                        tag: el.tagName,
                        text: t,
                        role: el.getAttribute('role') || '',
                        class: (el.className || '').substring(0, 100),
                        clickable: !!(el.onclick || el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'tab'),
                    });
                }
            }
            return results;
        }
    """)
    for tab in tabs:
        print(f"  <{tab['tag']}> text='{tab['text']}' role='{tab['role']}' clickable={tab['clickable']} class='{tab['class']}'")

    # Check for agreement checkboxes
    print("\n--- Checkbox/Agreement elements ---")
    checks = await page.evaluate("""
        () => {
            const results = [];
            for (const el of document.querySelectorAll('input[type="checkbox"], [role="checkbox"], label')) {
                const t = (el.textContent || '').trim().substring(0, 100);
                results.push({
                    tag: el.tagName,
                    type: el.type || '',
                    text: t,
                    checked: el.checked || false,
                    class: (el.className || '').substring(0, 100),
                });
            }
            return results;
        }
    """)
    for ch in checks:
        print(f"  <{ch['tag']}> type='{ch['type']}' text='{ch['text']}' checked={ch['checked']}")

    # Full page HTML dump (abbreviated)
    print("\n--- Login form area HTML (first 3000 chars) ---")
    form_html = await page.evaluate("""
        () => {
            // Try to find the main form
            const form = document.querySelector('form') ||
                         document.querySelector('[class*="login"]') ||
                         document.querySelector('[class*="sign"]') ||
                         document.querySelector('[class*="auth"]') ||
                         document.querySelector('main');
            if (form) return form.outerHTML.substring(0, 3000);
            return document.body.innerHTML.substring(0, 3000);
        }
    """)
    print(form_html)

    print("\n" + "=" * 60)
    print("Inspection complete. Browser will close in 10 seconds.")
    print("Check debug_deepseek_*.png screenshots.")
    print("=" * 60)
    await asyncio.sleep(10)
    await browser.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(inspect())
