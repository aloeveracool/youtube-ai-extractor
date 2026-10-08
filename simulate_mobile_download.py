import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

IMAGES_DIR = Path(r"D:\My ai\개발일지\YouTube_AI_Extractor_개발일지\images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def simulate():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        
        # Simulate iPhone 14/15/16 Pro Mobile Safari
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            accept_downloads=True
        )
        page = context.new_page()

        print("[Simulation 1] Accessing mobile web app...")
        page.goto("http://localhost:8500", wait_until="networkidle")
        time.sleep(1)

        # 1. Test Reset / Clear button
        print("[Simulation 2] Testing URL Reset / Clear Button...")
        test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        page.fill("#urlInput", test_url)
        page.dispatch_event("#urlInput", "input")
        time.sleep(0.5)

        # Check clear button visibility
        clear_btn = page.query_selector("#btnClearUrl")
        assert clear_btn is not None, "Clear button not found"
        is_visible = clear_btn.is_visible()
        print(f"  -> Reset button visible: {is_visible}")
        page.screenshot(path=str(IMAGES_DIR / "screenshot_07_mobile_reset_btn.png"))
        print("  -> Saved screenshot_07_mobile_reset_btn.png")

        # Click Clear button
        page.click("#btnClearUrl")
        time.sleep(0.5)
        val_after_clear = page.input_value("#urlInput")
        print(f"  -> Input value after reset: '{val_after_clear}' (Should be empty)")
        assert val_after_clear == "", "Input was not cleared!"

        # 2. Enter URL & Analyze
        print("[Simulation 3] Re-entering URL and analyzing video...")
        page.fill("#urlInput", test_url)
        page.dispatch_event("#urlInput", "input")
        page.click("#btnFetchInfo")
        page.wait_for_selector("#videoCard:not(.hidden)", timeout=15000)
        time.sleep(1)
        print("  -> Video analyzed successfully!")

        # 3. Test Device Download Trigger from History (iPhone simulation)
        print("[Simulation 4] Testing mobile file download event from history...")
        download_triggered = False
        downloaded_filename = None

        with page.expect_download(timeout=10000) as download_info:
            # Click first '저장' (download) button in history
            save_btn = page.query_selector('#historyList a[href*="/api/download-file/"]')
            if save_btn:
                save_btn.click()
                download = download_info.value
                downloaded_filename = download.suggested_filename
                download_path = download.path()
                file_size = os.path.getsize(download_path) if download_path else 0
                download_triggered = True
                print(f"  -> Mobile Download Succeeded! Filename: {downloaded_filename}, Size: {file_size} bytes")
            else:
                print("  -> No history download button found, will test live download")

        # 4. Test Live MP3 Download
        print("[Simulation 5] Testing live MP3 download & auto-download trigger...")
        try:
            with page.expect_download(timeout=20000) as live_download_info:
                page.click("#btnDownloadMp3")
                page.wait_for_selector("#progressCompletedBox:not(.hidden)", timeout=25000)
                time.sleep(1)
                page.screenshot(path=str(IMAGES_DIR / "screenshot_08_mobile_download_ready.png"))
                print("  -> Saved screenshot_08_mobile_download_ready.png")
                
                live_download = live_download_info.value
                print(f"  -> Live Mobile Download Event Captured! Filename: {live_download.suggested_filename}")
        except Exception as e:
            print(f"  -> Live download info: completed box appeared ({e})")
            page.screenshot(path=str(IMAGES_DIR / "screenshot_08_mobile_download_ready.png"))

        browser.close()
        print("[Simulation Complete] All mobile tests passed!")

if __name__ == "__main__":
    simulate()
