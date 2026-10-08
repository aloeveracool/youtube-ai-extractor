import time
from pathlib import Path
from playwright.sync_api import sync_playwright

IMAGES_DIR = Path(r"D:\My ai\개발일지\YouTube_AI_Extractor_개발일지\images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        print("[1] Opening Main Dashboard...")
        page.goto("http://localhost:8500", wait_until="networkidle")
        time.sleep(1)
        page.screenshot(path=str(IMAGES_DIR / "screenshot_01_main_dashboard.png"))
        print("  -> Saved screenshot_01_main_dashboard.png")

        print("[2] Analyzing Video...")
        page.fill("#urlInput", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        page.click("#btnFetchInfo")
        page.wait_for_selector("#videoCard:not(.hidden)", timeout=15000)
        time.sleep(1.5)
        page.screenshot(path=str(IMAGES_DIR / "screenshot_02_video_analyzed.png"))
        print("  -> Saved screenshot_02_video_analyzed.png")

        print("[3] Requesting AI Summary...")
        page.click("#btnSummarize")
        page.wait_for_selector("#summarySection:not(.hidden)", timeout=15000)
        time.sleep(2.5)
        page.screenshot(path=str(IMAGES_DIR / "screenshot_03_ai_summary.png"))
        print("  -> Saved screenshot_03_ai_summary.png")

        print("[4] Opening Settings Modal...")
        page.click("#btnOpenSettings")
        page.wait_for_selector("#settingsModal:not(.hidden)", timeout=5000)
        time.sleep(1)
        page.screenshot(path=str(IMAGES_DIR / "screenshot_04_settings_modal.png"))
        print("  -> Saved screenshot_04_settings_modal.png")

        print("[5] Closing Settings & Opening Media Player...")
        page.click("#btnCloseSettings")
        time.sleep(0.5)
        
        play_btn = page.query_selector(".btn-play")
        if play_btn:
            play_btn.click()
            page.wait_for_selector("#playerModal:not(.hidden)", timeout=5000)
            time.sleep(1)
            page.screenshot(path=str(IMAGES_DIR / "screenshot_05_media_player.png"))
            print("  -> Saved screenshot_05_media_player.png")

        browser.close()
        print("All screenshots captured successfully!")

if __name__ == "__main__":
    run()
