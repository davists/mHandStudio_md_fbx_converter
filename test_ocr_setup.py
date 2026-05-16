"""
Quick test script to verify OCR setup is working correctly.
Opens Notepad and tries to find/click UI elements using OCR.
"""

import sys
import time
import logging
import subprocess
from pathlib import Path
import pyautogui as ag

# Import OCR helper
try:
    from ocr_ui_helper import (
        check_tesseract_installation,
        find_text_on_screen,
        click_button_by_text,
        capture_screen
    )
except ImportError:
    print("Error: Could not import ocr_ui_helper.py")
    print("Make sure you're running this from the correct directory.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def test_tesseract():
    """Test 1: Verify Tesseract is installed"""
    log.info("=" * 70)
    log.info("TEST 1: Tesseract Installation")
    log.info("=" * 70)
    
    if check_tesseract_installation():
        log.info("✓ PASS: Tesseract is installed and working")
        return True
    else:
        log.error("✗ FAIL: Tesseract is not installed or not in PATH")
        log.error("  Install from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False


def test_screen_capture():
    """Test 2: Screen capture functionality"""
    log.info("=" * 70)
    log.info("TEST 2: Screen Capture")
    log.info("=" * 70)
    
    try:
        img = capture_screen()
        height, width = img.shape[:2]
        log.info(f"  Captured {width}x{height} screenshot")
        
        # Save to disk
        debug_dir = Path("_ocr_debug")
        debug_dir.mkdir(exist_ok=True)
        
        import cv2
        cv2.imwrite(str(debug_dir / "test_capture.png"), img)
        log.info(f"  Saved to {debug_dir / 'test_capture.png'}")
        log.info("✓ PASS: Screen capture working")
        return True
        
    except Exception as e:
        log.error(f"✗ FAIL: Screen capture failed: {e}")
        return False


def test_notepad_ocr():
    """Test 3: OCR on real application (Notepad)"""
    log.info("=" * 70)
    log.info("TEST 3: OCR on Notepad")
    log.info("=" * 70)
    
    log.info("Opening Notepad...")
    try:
        notepad_proc = subprocess.Popen(["notepad.exe"])
        time.sleep(2)  # Wait for Notepad to open
        
        # Type some test text
        log.info("Typing test text...")
        ag.typewrite("Hello OCR Test!", interval=0.1)
        time.sleep(0.5)
        
        # Try to find "File" menu
        log.info("Searching for 'File' menu...")
        debug_dir = Path("_ocr_debug")
        debug_dir.mkdir(exist_ok=True)
        
        result = find_text_on_screen(
            "File",
            confidence_threshold=0.5,
            debug_save=debug_dir / "test_notepad_file.png"
        )
        
        if result:
            x, y, w, h = result
            log.info(f"  ✓ Found 'File' at ({x}, {y}) - size {w}x{h}")
            log.info(f"  Debug image saved to {debug_dir / 'test_notepad_file.png'}")
            
            # Try to find "Edit" menu
            log.info("Searching for 'Edit' menu...")
            result2 = find_text_on_screen(
                "Edit",
                confidence_threshold=0.5,
                debug_save=debug_dir / "test_notepad_edit.png"
            )
            
            if result2:
                log.info("  ✓ Found 'Edit' menu")
            else:
                log.warning("  ⚠ Could not find 'Edit' menu (but File was found, so OCR is working)")
            
            # Close Notepad without saving
            log.info("Closing Notepad...")
            ag.hotkey("alt", "f4")
            time.sleep(0.5)
            
            # Try to find "Don't Save" button
            log.info("Searching for 'Don't Save' or 'No' button...")
            for text in ["Don't Save", "No", "Não Salvar"]:
                if click_button_by_text(text, retry_count=1, debug_dir=debug_dir):
                    log.info(f"  ✓ Clicked '{text}' button using OCR")
                    break
            else:
                log.warning("  Could not find save dialog button, pressing N key")
                ag.press("n")
            
            time.sleep(0.5)
            
            log.info("✓ PASS: OCR successfully detected text in Notepad")
            return True
        else:
            log.error("✗ FAIL: Could not find 'File' menu in Notepad")
            log.error(f"  Check debug image: {debug_dir / 'test_notepad_file_failed.png'}")
            
            # Try to close Notepad anyway
            ag.hotkey("alt", "f4")
            time.sleep(0.3)
            ag.press("n")  # Don't save
            
            return False
            
    except Exception as e:
        log.error(f"✗ FAIL: Notepad OCR test failed: {e}")
        # Try to kill notepad
        try:
            notepad_proc.terminate()
        except:
            pass
        return False


def test_window_text():
    """Test 4: Find text in active window (VS Code or any window)"""
    log.info("=" * 70)
    log.info("TEST 4: OCR on Current Window")
    log.info("=" * 70)
    
    log.info("Searching for common UI text in current screen...")
    log.info("(This will search for typical Windows UI elements)")
    
    debug_dir = Path("_ocr_debug")
    debug_dir.mkdir(exist_ok=True)
    
    # Common text that appears in Windows UI
    test_words = [
        "File", "Edit", "View", "Help", "Tools", "Window",
        "Start", "Search", "Close", "Minimize", "Maximize"
    ]
    
    found_count = 0
    for word in test_words:
        result = find_text_on_screen(
            word,
            confidence_threshold=0.5,
            debug_save=debug_dir / f"test_window_{word}.png"
        )
        if result:
            log.info(f"  ✓ Found: '{word}'")
            found_count += 1
    
    if found_count > 0:
        log.info(f"✓ PASS: Found {found_count}/{len(test_words)} common UI elements")
        return True
    else:
        log.warning("✗ FAIL: Could not find any common UI text")
        log.warning("  This might mean OCR is not working properly")
        return False


def main():
    """Run all OCR tests"""
    log.info("╔" + "=" * 68 + "╗")
    log.info("║" + " " * 20 + "OCR SETUP TEST SUITE" + " " * 28 + "║")
    log.info("╚" + "=" * 68 + "╝")
    log.info("")
    
    results = {
        "Tesseract Installation": test_tesseract(),
        "Screen Capture": test_screen_capture(),
        "Notepad OCR Test": test_notepad_ocr(),
        "Window OCR Test": test_window_text(),
    }
    
    # Summary
    log.info("")
    log.info("=" * 70)
    log.info("TEST SUMMARY")
    log.info("=" * 70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        log.info(f"  {status}  {test_name}")
    
    log.info("=" * 70)
    log.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        log.info("")
        log.info("✓ ALL TESTS PASSED!")
        log.info("Your OCR setup is working correctly.")
        log.info("You can now use mhand_to_fbx_ocr.py")
        return 0
    else:
        log.error("")
        log.error("✗ SOME TESTS FAILED")
        log.error("Please fix the issues above before using OCR automation.")
        log.error("")
        log.error("Common issues:")
        log.error("  1. Tesseract not installed → Download from GitHub")
        log.error("  2. Tesseract not in PATH → Reinstall with PATH option")
        log.error("  3. Wrong Tesseract path → Edit ocr_ui_helper.py")
        log.error("")
        log.error("Debug images saved to: _ocr_debug/")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        log.exception(f"Unexpected error: {e}")
        sys.exit(1)
