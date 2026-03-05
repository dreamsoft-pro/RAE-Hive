import asyncio
from playwright.async_api import async_playwright
import os

async def run_audit(url):
    print(f"🚀 Starting Deep Visual Audit for: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        try:
            print("-> Navigating to Login Page...")
            await page.goto("http://screenwatcher.printdisplay.pl/admin/login/", wait_until="networkidle")
            
            # Próbujemy standardowych danych dev
            print("-> Attempting dev login...")
            await page.fill('input[name="username"]', "admin")
            await page.fill('input[name="password"]', "password") # Zmienię jeśli znasz inne
            await page.click('button[type="submit"]')
            await asyncio.sleep(2)

            print(f"-> Navigating to Target: {url}")
            await page.goto(url, wait_until="networkidle")

            # KLIKAMY W GUZIK POMOCY (?)
            print("-> Searching for RAE Help Trigger...")
            trigger = await page.wait_for_selector("#rae-v2-trigger", timeout=10000)
            if trigger:
                print("-> CLICKING HELP BUTTON!")
                await trigger.click()
                
                # Czekamy na załadowanie iframe i analizę Agenta
                print("-> Waiting for Agent Analysis (30s)...")
                await asyncio.sleep(30)
                
                # Robimy screenshot z otwartym panelem
                os.makedirs("/app/debug", exist_ok=True)
                await page.screenshot(path="/app/debug/audit_with_panel.png")
                print("✅ Screenshot with panel saved.")

            print("\n--- KONSOLA BŁĘDÓW ---")
            for log in console_logs:
                if "error" in log.lower() or "failed" in log.lower():
                    print(log)
            print("----------------------\n")

        except Exception as e:
            print(f"❌ Audit failed: {e}")
            await page.screenshot(path="/app/debug/audit_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    target_url = "http://screenwatcher.printdisplay.pl/admin/auth/user/"
    asyncio.run(run_audit(target_url))
