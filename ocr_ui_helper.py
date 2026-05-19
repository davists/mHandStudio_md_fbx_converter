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
        
        # Collect all detected text for debugging
        detected_texts = []
        
        # Search through detected text
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            detected_text = data['text'][i].strip()
            conf = int(data['conf'][i]) / 100.0  # Convert to 0-1 range
            
            if not detected_text or conf < confidence_threshold:
                continue
            
            # Log all detected text for debugging
            detected_texts.append(f"'{detected_text}'({conf:.0%})")
            
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
        
        # Log all detected text if search failed
        # if detected_texts:
            # log.info(f"  OCR detected (invert={invert}): {', '.join(detected_texts[:20])}")  # Show first 20
            # if len(detected_texts) > 20:
                # log.info(f"  ... and {len(detected_texts) - 20} more texts")
    
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


def click_checkbox_by_text(
    checkbox_label: str,
    search_region=None,
    offset_x: int = -20,
    retry_count: int = 2,
    debug_dir: Optional[Path] = None
) -> bool:
    """
    Finds a checkbox by its label text and clicks it.
    
    Checkboxes typically have text to their right, so we click to the left of the text.
    
    Args:
        checkbox_label: Text label next to the checkbox (e.g., "NotShowToday", "Remember me")
        search_region: Region to search in
        offset_x: Horizontal offset from text (negative = left of text, where checkbox is)
        retry_count: Number of attempts
        debug_dir: Directory for debug screenshots
        
    Returns:
        True if checkbox was found and clicked
    """
    for attempt in range(retry_count):
        debug_save = None
        if debug_dir:
            debug_save = debug_dir / f"checkbox_{checkbox_label.replace(' ', '_')}_attempt_{attempt+1}.png"
        
        log.info(f"Looking for checkbox '{checkbox_label}' (attempt {attempt+1}/{retry_count})...")
        
        result = find_text_on_screen(
            checkbox_label,
            region=search_region,
            confidence_threshold=0.4,  # Reduzido de 0.5 para 0.4 para maior sensibilidade
            debug_save=debug_save
        )
        
        if result:
            x, y, w, h = result
            
            # Tenta múltiplas posições para clicar no checkbox
            offsets_to_try = [
                (offset_x, 0),           # Padrão: à esquerda
                (-15, 0),                # Mais perto do texto
                (-25, 0),                # Mais longe do texto
                (-30, 0),                # Ainda mais longe
                (offset_x, h // 2),      # À esquerda, centro vertical
            ]
            
            for i, (off_x, off_y) in enumerate(offsets_to_try):
                click_x = x + off_x
                click_y = y + h // 2 + off_y
                
                log.info(f"  ✓ Found checkbox label at ({x}, {y}), trying click at ({click_x}, {click_y}) [offset {i+1}]")
                ag.click(click_x, click_y)
                time.sleep(0.3)
                
                # Tenta apenas o primeiro offset no primeiro attempt, depois tenta todos
                if attempt == 0 and i == 0:
                    break
            
            return True
        
        if attempt < retry_count - 1:
            time.sleep(0.5)
    
    log.warning(f"Could not find checkbox '{checkbox_label}'")
    return False


def handle_auto_update_dialog(
    window_region=None,
    debug_dir: Optional[Path] = None,
    timeout: float = 5.0
) -> bool:
    """
    Handles the Auto Update dialog that appears on mHandStudio startup.
    
    Detects the dialog by looking for "Update Now" text and clicks Cancel to close it.
    
    Args:
        window_region: Region to search (or None for full screen)
        debug_dir: Directory to save debug screenshots
        timeout: How long to wait for dialog to appear
        
    Returns:
        True if dialog was handled, False if dialog not found
    """
    log.info("Checking for Auto Update dialog...")
    
    # Create debug directory if needed
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        ag.screenshot(str(debug_dir / "00_startup_check_update_dialog.png"))
    
    # First check if Edit menu is already visible - if so, no dialog is present
    log.info("  Checking if Edit menu is already visible...")
    edit_check = find_text_on_screen("Edit", region=window_region, 
                                     confidence_threshold=0.6,
                                     debug_save=debug_dir / "00_check_edit_menu.png" if debug_dir else None)
    if edit_check:
        log.info("  ✓ Edit menu is already visible, no update dialog present")
        return False
    
    # Check if the dialog exists - look for "Update Now" or related text
    dialog_indicators = [
        "Update",
        "NewVersionDetected",
        "Update Now",
    ]
    
    dialog_found = False
    found_keyword = ""
    dialog_result = None
    for indicator in dialog_indicators:
        result = find_text_on_screen(
            indicator,
            region=window_region,
            confidence_threshold=0.4,
            debug_save=debug_dir / f"00_search_{indicator.replace(' ', '_')}.png" if debug_dir else None
        )
        if result:
            log.info(f"  ✓ Auto Update dialog detected (found '{indicator}')")
            dialog_found = True
            found_keyword = indicator
            dialog_result = result
            break
        time.sleep(0.15)
    
    if not dialog_found:
        log.info("  No Auto Update dialog found, continuing...")
        return False
    
    # Dialog exists, click X button to close it
    log.info(f"Auto Update dialog confirmado (palavra detectada: '{found_keyword}')")
    
    # Strategy: Find and click the X close button (top-right of dialog)
    log.info("Procurando botão X para fechar diálogo...")
    
    close_clicked = False
    
    # The X button is typically near the top-right of where we found the dialog text
    if dialog_result:
        x, y, w, h = dialog_result
        
        # Search for X button to the right and slightly above the dialog text
        # X button is usually in top-right corner of dialog
        x_search_x = x + w - 100  # Start near right side of detected text
        x_search_y = y - 50  # Look above the text (title bar area)
        x_search_w = 200
        x_search_h = 80
        
        x_button_region = (x_search_x, x_search_y, x_search_w, x_search_h)
        log.info(f"  Searching for X button in region: {x_button_region}")
        
        img = capture_screen(region=x_button_region)
        
        if debug_dir:
            cv2.imwrite(str(debug_dir / "02_x_button_region.png"), img)
        
        # Look for X button - try OCR first
        x_labels = ["X", "×", "x"]
        
        for label in x_labels:
            result = find_text_on_screen(
                label,
                region=x_button_region,
                confidence_threshold=0.3,
                debug_save=debug_dir / f"02_x_search_{label}.png" if debug_dir else None
            )
            if result:
                cx, cy, cw, ch = result
                click_x = cx + cw // 2
                click_y = cy + ch // 2
                log.info(f"  ✓ Found X button at ({click_x}, {click_y}), clicking...")
                ag.click(click_x, click_y)
                time.sleep(0.5)
                close_clicked = True
                break
    
    # Fallback: Try to find small square button in top-right of screen
    if not close_clicked:
        log.info("  Trying to detect X button visually...")
        
        # Capture top portion of screen where X button would be
        screen_width, screen_height = ag.size()
        top_right_region = (int(screen_width * 0.5), 0, int(screen_width * 0.5), int(screen_height * 0.3))
        
        img = capture_screen(region=top_right_region)
        
        if debug_dir:
            cv2.imwrite(str(debug_dir / "03_top_right_area.png"), img)
        
        # Look for small square-ish buttons (close buttons are typically square)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # X buttons are often light colored (white/light gray on dark background)
        # or dark on light background
        light_mask = cv2.inRange(gray, 200, 255)
        
        contours, _ = cv2.findContours(light_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        close_candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 100 < area < 1000:  # Small button-sized
                bx, by, bw, bh = cv2.boundingRect(contour)
                aspect_ratio = bw / float(bh) if bh > 0 else 0
                # Close buttons are squarish (aspect ratio close to 1)
                if 0.7 < aspect_ratio < 1.3 and 10 < bw < 50 and 10 < bh < 50:
                    close_candidates.append((bx, by, bw, bh, area))
        
        if close_candidates:
            # Sort by x position (rightmost first) - X is in top-right
            close_candidates.sort(key=lambda b: b[0], reverse=True)
            
            log.info(f"  Found {len(close_candidates)} X button candidates")
            
            if debug_dir:
                debug_img = img.copy()
                for i, (bx, by, bw, bh, _) in enumerate(close_candidates[:3]):
                    color = (0, 255, 0) if i == 0 else (0, 0, 255)
                    cv2.rectangle(debug_img, (bx, by), (bx + bw, by + bh), color, 2)
                    cv2.putText(debug_img, f"#{i+1}", (bx, by-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                cv2.imwrite(str(debug_dir / "04_x_button_candidates.png"), debug_img)
            
            # Click the rightmost candidate
            bx, by, bw, bh, _ = close_candidates[0]
            click_x = top_right_region[0] + bx + bw // 2
            click_y = top_right_region[1] + by + bh // 2
            
            log.info(f"  Clicking X button at ({click_x}, {click_y})")
            ag.click(click_x, click_y)
            time.sleep(0.5)
            close_clicked = True
    
    # Fallback: ESC key
    if not close_clicked:
        log.warning("  Could not find X button, trying ESC key...")
        ag.press("escape")
        time.sleep(0.5)
        close_clicked = True
    
    if debug_dir:
        ag.screenshot(str(debug_dir / "05_dialog_closed.png"))
    
    log.info("Auto Update dialog handled successfully")
    time.sleep(1)  # Wait for dialog to close
    
    return True


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
        test_texts = ["Edit"]
        for text in test_texts:
            result = find_text_on_screen(text, confidence_threshold=0.5)
            if result:
                log.info(f"  ✓ Found '{text}' at {result}")
                break
    else:
        log.error("✗ Please install Tesseract OCR first")
