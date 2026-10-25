import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto('http://127.0.0.1:8080')
        await page.wait_for_timeout(1000)

        initial_theme = await page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        initial_bg = await page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
        print(f"Initial theme: {initial_theme}, Body BG: {initial_bg}")

        # Check scrollHeight vs innerHeight
        scroll_height = await page.evaluate("() => document.documentElement.scrollHeight")
        inner_height = await page.evaluate("() => window.innerHeight")
        print(f"Scroll height: {scroll_height}, Inner height: {inner_height} (Fits 100vh: {scroll_height <= inner_height})")

        # Check loading banner visibility
        banner_display = await page.evaluate("() => window.getComputedStyle(document.getElementById('pipelineBanner')).display")
        print(f"Banner display when idle: {banner_display} (Hidden: {banner_display == 'none'})")

        # Click theme toggle to test dark mode
        await page.click('#btnThemeToggle')
        await page.wait_for_timeout(500)
        dark_theme = await page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        dark_bg = await page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
        print(f"Theme after click: {dark_theme}, Body BG: {dark_bg}")
        await page.screenshot(path="scratch_dark_mode.png")

        # Click again to test switch back to light
        await page.click('#btnThemeToggle')
        await page.wait_for_timeout(500)
        back_theme = await page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        back_bg = await page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
        print(f"Theme after 2nd click: {back_theme}, Body BG: {back_bg}")
        await page.screenshot(path="scratch_light_mode.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
