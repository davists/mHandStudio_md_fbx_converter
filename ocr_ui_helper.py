"""
OCR-based UI automation helper using Tesseract
Intelligently locates UI elements by reading screen text
"""

import logging
import time
from pathlib import Path
from typing import Tuple, Optional, List
import pyautogui as ag
import cv2
import numpy as np
import pytesseract

log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# OCR CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# Path to Tesseract executable (Windows default location)
# Change if Tesseract is installed elsewhere
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except Exception:
    log.warning("Tesseract path not set, using system default")


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN CAPTURE & OCR
# ══════════════════════════════════════════════════════════════════════════════

def capture_screen(region=None) -> np.ndarray:
    """
    Captures screenshot and returns as OpenCV image (BGR format).
    
    Args:
        region: Tuple (left, top, width, height) or None for full screen
        
    Returns:
        numpy array in BGR format
    """
    screenshot = ag.screenshot(region=region)
    # Convert PIL Image to numpy array (RGB)
    img_rgb = np.array(screenshot)
    # Convert RGB to BGR for OpenCV
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    return img_bgr


def preprocess_for_ocr(img: np.ndarray, invert=False) -> np.ndarray:
    """
    Preprocesses image for better OCR accuracy.
    
    Args:
        img: Input BGR image
        invert: If True, invert colors (useful for dark themes)
        
    Returns:
        Preprocessed grayscale image
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Increase contrast
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    
    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Threshold to binary
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    if invert:
        binary = cv2.bitwise_not(binary)
    
    return binary


def find_text_on_screen(
    text: str,
    region=None,
    confidence_threshold: float = 0.5,
    case_sensitive: bool = False,
    debug_save: Optional[Path] = None
) -> Optional[Tuple[int, int, int, int]]:
    """
    Finds text on screen using OCR and returns its bounding box.
    
    Args:
        text: Text to search for (can be partial match)
        region: Search region (left, top, width, height) or None for full screen
        confidence_threshold: Minimum confidence (0-1) to accept match
        case_sensitive: Whether to match case exactly
        debug_save: If provided, saves annotated debug image to this path
        
    Returns:
        Tuple (x, y, width, height) of text location, or None if not found
    """
    log.info(f"Searching for text: '{text}'")
    
    # Capture screen
    img = capture_screen(region)
    
    # Try both normal and inverted preprocessing
    for invert in [False, True]:
        processed = preprocess_for_ocr(img, invert=invert)
        
        # Run OCR with detailed data
        data = pytesseract.image_to_data(
            processed,
            output_type=pytesseract.Output.DICT,
            lang='eng',
            config='--psm 11'  # Sparse text mode
        )
        
        # Search through detected text
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            detected_text = data['text'][i].strip()
            conf = int(data['conf'][i]) / 100.0  # Convert to 0-1 range
            
            if not detected_text or conf < confidence_threshold:
                continue
            
            # Match text
            search_text = text if case_sensitive else text.lower()
            detected_lower = detected_text if case_sensitive else detected_text.lower()
            
            if search_text in detected_lower:
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                
                # Adjust coordinates if region was specified
                if region:
                    x += region[0]
                    y += region[1]
                
                log.info(f"✓ Found '{detected_text}' at ({x}, {y}) with {conf:.1%} confidence")
                
                # Save debug image if requested
                if debug_save:
                    debug_img = img.copy()
                    cv2.rectangle(debug_img, (x - (region[0] if region else 0), 
                                             y - (region[1] if region else 0)), 
                                 (x - (region[0] if region else 0) + w, 
                                  y - (region[1] if region else 0) + h), 
                                 (0, 255, 0), 2)
                    cv2.putText(debug_img, detected_text, 
                               (x - (region[0] if region else 0), y - (region[1] if region else 0) - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    cv2.imwrite(str(debug_save), debug_img)
                    log.info(f"  Debug image saved to {debug_save}")
                
                return (x, y, w, h)
    
    log.warning(f"✗ Text '{text}' not found on screen")
    
    # Save failed search image for debugging
    if debug_save:
        failed_path = debug_save.parent / f"{debug_save.stem}_failed.png"
        cv2.imwrite(str(failed_path), img)
        log.info(f"  Failed search image saved to {failed_path}")
    
    return None


def find_and_click_text(
    text: str,
    region=None,
    confidence_threshold: float = 0.5,
    offset_x: int = 0,
    offset_y: int = 0,
    click_center: bool = True,
    debug_save: Optional[Path] = None,
    wait_after: float = 0.5
) -> bool:
    """
    Finds text on screen and clicks it.
    
    Args:
        text: Text to find and click
        region: Search region or None for full screen
        confidence_threshold: Minimum OCR confidence
        offset_x, offset_y: Pixel offset from text position
        click_center: If True, clicks center of text box; if False, clicks top-left
        debug_save: Path to save debug image
        wait_after: Seconds to wait after clicking
        
    Returns:
        True if found and clicked, False otherwise
    """
    result = find_text_on_screen(text, region, confidence_threshold, debug_save=debug_save)
    
    if result:
        x, y, w, h = result
        
        # Calculate click position
        if click_center:
            click_x = x + w // 2 + offset_x
            click_y = y + h // 2 + offset_y
        else:
            click_x = x + offset_x
            click_y = y + offset_y
        
        log.info(f"  Clicking at ({click_x}, {click_y})")
        ag.click(click_x, click_y)
        time.sleep(wait_after)
        return True
    
    return False


# ══════════════════════════════════════════════════════════════════════════════
# HIGH-LEVEL UI ACTIONS
# ══════════════════════════════════════════════════════════════════════════════

def click_button_by_text(
    button_text: str,
    search_region=None,
    retry_count: int = 3,
    debug_dir: Optional[Path] = None
) -> bool:
    """
    Intelligently finds and clicks a button by its text label.
    Retries multiple times with slight delays.
    
    Args:
        button_text: Text on the button (e.g., "OK", "Export", "确定")
        search_region: Limit search to specific screen region
        retry_count: Number of times to retry if not found
        debug_dir: Directory to save debug screenshots
        
    Returns:
        True if clicked successfully
    """
    for attempt in range(retry_count):
        debug_save = None
        if debug_dir:
            debug_save = debug_dir / f"click_{button_text}_attempt_{attempt+1}.png"
        
        log.info(f"Looking for button '{button_text}' (attempt {attempt+1}/{retry_count})...")
        
        if find_and_click_text(
            button_text,
            region=search_region,
            confidence_threshold=0.6,
            debug_save=debug_save
        ):
            return True
        
        if attempt < retry_count - 1:
            log.info(f"  Retrying in 1 second...")
            time.sleep(1)
    
    log.error(f"Failed to find button '{button_text}' after {retry_count} attempts")
    return False


def find_dropdown_option(
    option_text: str,
    dropdown_region=None,
    debug_dir: Optional[Path] = None
) -> Optional[Tuple[int, int]]:
    """
    Finds a specific option in an opened dropdown menu.
    
    Args:
        option_text: Text of the option to find (e.g., "FBX binary")
        dropdown_region: Region where dropdown is displayed
        debug_dir: Directory for debug images
        
    Returns:
        (x, y) coordinates of the option center, or None if not found
    """
    debug_save = None
    if debug_dir:
        debug_save = debug_dir / f"dropdown_option_{option_text}.png"
    
    result = find_text_on_screen(
        option_text,
        region=dropdown_region,
        confidence_threshold=0.6,
        debug_save=debug_save
    )
    
    if result:
        x, y, w, h = result
        return (x + w // 2, y + h // 2)
    
    return None


def smart_dropdown_select(
    dropdown_label: str,
    option_text: str,
    window_region=None,
    debug_dir: Optional[Path] = None
) -> bool:
    """
    Intelligently opens a dropdown and selects an option by text.
    
    Args:
        dropdown_label: Label/text near the dropdown field
        option_text: Text of the option to select
        window_region: Region of the dialog/window
        debug_dir: Debug directory
        
    Returns:
        True if successful
    """
    log.info(f"Smart dropdown select: '{dropdown_label}' → '{option_text}'")
    
    # Find and click the dropdown field
    if not find_and_click_text(dropdown_label, region=window_region, 
                               confidence_threshold=0.5, wait_after=0.5,
                               debug_save=debug_dir / f"dropdown_{dropdown_label}.png" if debug_dir else None):
        log.warning(f"Could not find dropdown labeled '{dropdown_label}'")
        # Try opening with keyboard shortcuts anyway
        ag.hotkey("alt", "down")
        time.sleep(0.5)
    
    # Wait for dropdown to open
    time.sleep(0.8)
    
    # Find the option
    option_pos = find_dropdown_option(option_text, dropdown_region=window_region, debug_dir=debug_dir)
    
    if option_pos:
        x, y = option_pos
        log.info(f"  Clicking option at ({x}, {y})")
        ag.click(x, y)
        time.sleep(0.5)
        return True
    else:
        log.warning(f"Could not find dropdown option '{option_text}'")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def verify_text_exists(
    text: str,
    region=None,
    timeout: float = 5.0
) -> bool:
    """
    Waits for text to appear on screen within timeout period.
    Useful for verifying that dialogs opened or actions completed.
    
    Args:
        text: Text to look for
        region: Search region
        timeout: Maximum seconds to wait
        
    Returns:
        True if text found within timeout
    """
    deadline = time.time() + timeout
    
    while time.time() < deadline:
        if find_text_on_screen(text, region=region, confidence_threshold=0.6):
            return True
        time.sleep(0.5)
    
    return False


def check_tesseract_installation() -> bool:
    """
    Verifies that Tesseract OCR is installed and accessible.
    
    Returns:
        True if Tesseract is working
    """
    try:
        version = pytesseract.get_tesseract_version()
        log.info(f"Tesseract OCR version: {version}")
        return True
    except Exception as e:
        log.error(f"Tesseract OCR not found: {e}")
        log.error("Install from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False


if __name__ == "__main__":
    # Test OCR functionality
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    
    log.info("Testing OCR UI Helper...")
    
    if check_tesseract_installation():
        log.info("✓ Tesseract is installed and working")
        
        # Test screen capture
        log.info("Capturing full screen...")
        img = capture_screen()
        log.info(f"  Captured {img.shape[1]}x{img.shape[0]} image")
        
        # Test text finding (will search for common Windows UI text)
        test_texts = ["Start", "Search", "File", "Edit", "View"]
        for text in test_texts:
            result = find_text_on_screen(text, confidence_threshold=0.5)
            if result:
                log.info(f"  ✓ Found '{text}' at {result}")
                break
    else:
        log.error("✗ Please install Tesseract OCR first")
