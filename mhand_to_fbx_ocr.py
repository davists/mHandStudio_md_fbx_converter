"""
OCR-Enhanced version of mhand_to_fbx.py
Uses Tesseract OCR to intelligently locate UI elements
"""

import argparse
import subprocess
import sys
import time
import shutil
import logging
from pathlib import Path
import pyautogui as ag
import numpy as np

# Import OCR helper
from ocr_ui_helper import (
    click_button_by_text,
    smart_dropdown_select,
    find_and_click_text,
    verify_text_exists,
    check_tesseract_installation,
    find_text_on_screen
)

# Try to import OpenCV for advanced image detection
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logging.warning("OpenCV not available, template matching disabled")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════
CFG = {
    "mhand_exe":       r"C:\Users\Locatech\Downloads\mHandStudio\mHandStudio\mHandStudio.exe",
    "output_dir":      None,  # Se None, salva na mesma pasta do .md
    "startup_timeout": 30,
    "ui_delay":        0.8,
    "window_title":    "mHandStudio",
    "force_restart":   True,
    "fbx_format":      "binary",
    "use_ocr":         True,  # NEW: Enable OCR-based UI detection
}


def close_mhand_studio():
    """Fecha todas as instâncias do mHand Studio"""
    import psutil
    
    log.info("Procurando processos do mHand Studio para fechar...")
    closed = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'mHandStudio' in proc.info['name']:
                log.info("  Fechando processo: %s (PID: %d)", proc.info['name'], proc.info['pid'])
                proc.terminate()
                closed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if closed:
        log.info("Aguardando processos fecharem...")
        time.sleep(2)


def find_or_launch_mhand(force_restart=True):
    """Inicia mHand Studio"""
    import pygetwindow as gw

    if force_restart:
        close_mhand_studio()
    else:
        log.info("Procurando mHand Studio...")
        wins = [w for w in gw.getAllWindows() if CFG["window_title"] in w.title]
        if wins:
            log.info("mHand Studio já está aberto.")
            try:
                wins[0].activate()
            except Exception:
                pass
            time.sleep(CFG["ui_delay"])
            return wins[0]

    exe = CFG["mhand_exe"]
    if not Path(exe).exists():
        log.error("Executável não encontrado: %s", exe)
        sys.exit(1)

    log.info("Iniciando mHand Studio...")
    subprocess.Popen([exe])

    deadline = time.time() + CFG["startup_timeout"]
    while time.time() < deadline:
        time.sleep(1.5)
        wins = [w for w in gw.getAllWindows() if CFG["window_title"] in w.title]
        if wins:
            log.info("mHand Studio aberto.")
            try:
                wins[0].activate()
            except Exception:
                pass
            log.info("Aguardando mHandStudio carregar completamente...")
            time.sleep(5)
            return wins[0]

    log.error("Timeout: mHand Studio não abriu em %ds.", CFG["startup_timeout"])
    sys.exit(1)


def find_export_button_opencv(win, plus_position, debug_dir):
    """
    Use OpenCV to find the export button by detecting buttons in the bottom toolbar.
    Returns (x, y) position of export button, or None if not found.
    """
    if not OPENCV_AVAILABLE:
        return None
    
    try:
        import cv2
        
        wl, wt = win.left, win.top
        ww, wh = win.width, win.height
        
        # Capture the bottom toolbar area
        toolbar_region = (wl, wt + int(wh * 0.88), int(ww * 0.25), int(wh * 0.12))
        screenshot = ag.screenshot(region=toolbar_region)
        
        # Convert PIL image to OpenCV format
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Save debug image
        cv2.imwrite(str(debug_dir / "05_toolbar_opencv.png"), img)
        
        # Detect edges to find button outlines
        edges = cv2.Canny(gray, 50, 150)
        cv2.imwrite(str(debug_dir / "05_toolbar_edges.png"), edges)
        
        # Find contours (potential buttons)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size (buttons are typically 20-50 pixels)
        button_candidates = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            # Filter: reasonable size and roughly square/rectangular
            if 200 < area < 2000 and 0.5 < w/h < 2.0:
                button_candidates.append((x, y, w, h))
        
        if not button_candidates:
            log.warning("  No button candidates found by OpenCV")
            return None
        
        # Sort by X position (left to right)
        button_candidates.sort(key=lambda b: b[0])
        
        # If we have plus_position, find the rightmost button (export is on the right)
        if button_candidates:
            # Take the rightmost button as export button
            rightmost = button_candidates[-1]
            x, y, w, h = rightmost
            
            # Convert back to screen coordinates
            export_x = toolbar_region[0] + x + w // 2
            export_y = toolbar_region[1] + y + h // 2
            
            log.info(f"  ✓ OpenCV found {len(button_candidates)} buttons, using rightmost at ({export_x}, {export_y})")
            
            # Draw rectangles on debug image
            for bx, by, bw, bh in button_candidates:
                cv2.rectangle(img, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 3)  # Highlight selected
            cv2.imwrite(str(debug_dir / "05_toolbar_buttons_detected.png"), img)
            
            return (export_x, export_y)
    
    except Exception as e:
        log.warning(f"  OpenCV detection failed: {e}")
    
    return None


def handle_export_dialog_ocr(win, fbx_path: Path):
    """
    OCR-ENHANCED Export Dialog Handler
    
    Uses Tesseract OCR to find UI elements by their text labels.
    Works with English menus.
    
    Expected dialog (English):
    ┌─────────────────────────────────┐
    │ Data Export                      │
    │ Output Folder  [path] [...]      │
    │ File Name      [name]            │
    │ Export Type    [FBX ▾]           │
    │ Rotation Order [YXZ ▾]          │
    │                [  OK  ]          │
    └─────────────────────────────────┘
    
    Or Chinese (数据导出):
    Same layout with Chinese labels
    """
    log.info("=== OCR-Enhanced Export Dialog ===")
    
    # Get window region for focused search
    wl, wt = win.left, win.top
    ww, wh = win.width, win.height
    window_region = (wl, wt, ww, wh)
    
    # Create debug directory
    debug_dir = fbx_path.parent / "_ocr_debug"
    debug_dir.mkdir(exist_ok=True)
    
    # Screenshot initial state
    ag.screenshot(str(debug_dir / "01_dialog_initial.png"))
    time.sleep(0.5)
    
    # ── File Name (Use OCR to locate the field) ──────────────────────────────────────────
    log.info("Setting filename: %s", fbx_path.stem)
    
    # Try to find "File Name" or "文件名" label
    filename_labels = ["File Name", "Filename", "文件名", "Name"]
    filename_found = False
    
    for label in filename_labels:
        result = find_text_on_screen(label, region=window_region, confidence_threshold=0.5,
                                     debug_save=debug_dir / f"02_search_{label}.png")
        if result:
            log.info(f"  Found filename field by label: '{label}'")
            x, y, w, h = result
            # Click to the right of the label (where the text field should be)
            click_x = x + w + 50
            click_y = y + h // 2
            ag.click(click_x, click_y)
            time.sleep(0.4)
            filename_found = True
            break
    
    if not filename_found:
        log.warning("  Could not find filename field by OCR, using keyboard navigation")
        # Fallback: use Tab to navigate to filename field
        ag.press("tab")
        time.sleep(0.3)
    
    # Enter filename
    ag.hotkey("ctrl", "a")
    time.sleep(0.2)
    ag.typewrite(fbx_path.stem, interval=0.04)
    time.sleep(0.3)
    ag.screenshot(str(debug_dir / "03_filename_entered.png"))
    
    # ── Export Type / Format (Use OCR to find FBX option) ──────────────────────────────
    log.info("Selecting FBX format using OCR...")
    
    # Try to find and click "Export Type" or "导出类型" field
    format_labels = ["Export Type", "Export Format", "导出类型", "Format", "Type"]
    format_found = False
    
    for label in format_labels:
        result = find_text_on_screen(label, region=window_region, confidence_threshold=0.5,
                                     debug_save=debug_dir / f"04_search_{label}.png")
        if result:
            log.info(f"  Found format field by label: '{label}'")
            x, y, w, h = result
            # Click on the dropdown (to the right of label)
            click_x = x + w + 50
            click_y = y + h // 2
            ag.click(click_x, click_y)
            time.sleep(0.5)
            format_found = True
            break
    
    if not format_found:
        log.warning("  Could not find format field by OCR, using Tab navigation")
        ag.press("tab")
        time.sleep(0.3)
    
    # Open dropdown with keyboard
    log.info("  Opening format dropdown...")
    ag.hotkey("alt", "down")
    time.sleep(0.8)
    ag.screenshot(str(debug_dir / "05_dropdown_opened.png"))
    
    # Try to find "FBX binary" option using OCR
    fbx_options = ["FBX binary", "FBX Binary", "binary"]
    fbx_found = False
    
    log.info("  Searching for 'FBX binary' option in dropdown...")
    for option_text in fbx_options:
        result = find_text_on_screen(option_text, region=window_region, 
                                     confidence_threshold=0.5,
                                     debug_save=debug_dir / f"06_search_{option_text}.png")
        if result:
            log.info(f"  ✓ Found FBX option by OCR: '{option_text}'")
            x, y, w, h = result
            # Click on the option
            click_x = x + w // 2
            click_y = y + h // 2
            ag.click(click_x, click_y)
            time.sleep(0.5)
            fbx_found = True
            break
    
    if not fbx_found:
        log.warning("  Could not find 'FBX binary' by OCR, using keyboard navigation")
        # Fallback: keyboard navigation
        # HOME to go to top, then DOWN to navigate
        ag.press("home")
        time.sleep(0.5)
        
        # Navigate to FBX binary (usually position 4)
        for i in range(3):
            ag.press("down")
            time.sleep(0.5)
        
        # Confirm
        ag.press("enter")
        time.sleep(0.5)
    
    ag.screenshot(str(debug_dir / "07_format_selected.png"))
    
    # ── OK Button (Use OCR to find Confirm button) ────────────────────────────────────────
    log.info("Looking for OK/Confirm button...")
    
    # Try multiple possible button texts
    ok_texts = ["OK", "确定", "Confirm", "Export", "导出"]
    ok_clicked = False
    
    for ok_text in ok_texts:
        if click_button_by_text(ok_text, search_region=window_region, 
                               retry_count=2, debug_dir=debug_dir):
            log.info(f"  ✓ Clicked OK button: '{ok_text}'")
            ok_clicked = True
            break
    
    if not ok_clicked:
        log.warning("  Could not find OK button by OCR, trying Enter key")
        ag.press("enter")
        time.sleep(0.5)
    
    ag.screenshot(str(debug_dir / "08_dialog_confirmed.png"))
    time.sleep(CFG["ui_delay"] * 2)
    
    log.info("Export dialog completed using OCR")


def export_fbx_via_ui_ocr(md_path: Path, fbx_path: Path) -> bool:
    """
    OCR-enhanced FBX export via mHandStudio UI.
    Adapts to any resolution and UI language (English/Chinese).
    
    Workflow:
      1. Switch to Edit mode (OCR-based menu click)
      2. Add .md file
      3. Load on timeline
      4. Export to FBX with OCR-based dialog handling
    """
    ag.FAILSAFE = True
    ag.PAUSE = 0.1

    win = find_or_launch_mhand()
    
    wl, wt = win.left, win.top
    ww, wh = win.width, win.height
    log.info("Window: (%d,%d) %dx%d", wl, wt, ww, wh)
    
    try:
        win.activate()
        time.sleep(1)
    except Exception:
        pass
    
    # Create debug directory
    debug_dir = fbx_path.parent / "_ocr_debug"
    debug_dir.mkdir(exist_ok=True)
    
    # Wait for interface to load
    log.info("Waiting for interface to load...")
    time.sleep(3)
    ag.screenshot(str(debug_dir / "00_initial.png"))
    
    # ── Step 1: Click Edit menu using OCR ─────────────────────────────────────
    log.info("Step 1: Clicking Edit menu using OCR...")
    menu_bar_region = (wl, wt, ww, int(wh * 0.08))
    edit_labels = ["Edit", "编辑"]
    edit_clicked = False
    
    for label in edit_labels:
        result = find_text_on_screen(label, region=menu_bar_region, 
                                    confidence_threshold=0.6,
                                    debug_save=debug_dir / f"01_search_menu_{label}.png")
        if result:
            x, y, w, h = result
            click_x = x + w // 2
            click_y = y + h // 2
            log.info(f"  ✓ Found '{label}' menu at ({click_x}, {click_y})")
            ag.click(click_x, click_y)
            time.sleep(CFG["ui_delay"] * 2)
            ag.screenshot(str(debug_dir / "01_edit_menu_clicked.png"))
            edit_clicked = True
            break
    
    if not edit_clicked:
        log.warning("  Could not find Edit menu by OCR, using fallback coordinates")
        menu_y = wt + int(wh * 0.047)
        btn_edit_menu_x = wl + int(ww * 0.10)
        ag.click(btn_edit_menu_x, menu_y)
        time.sleep(CFG["ui_delay"] * 2)
        ag.screenshot(str(debug_dir / "01_edit_menu_clicked_fallback.png"))
        edit_clicked = True  # Assume fallback worked
    
    if not edit_clicked:
        log.error("✗ Step 1 FAILED: Could not click Edit menu")
        return False
    
    # ── Step 2: Click + button using OCR ───────────────────────────────────────
    log.info("Step 2: Finding and clicking + button using OCR...")
    
    # Search for + button in bottom area of window
    bottom_region = (wl, wt + int(wh * 0.8), ww, int(wh * 0.2))
    
    plus_clicked = False
    plus_position = None
    result = find_text_on_screen("+", region=bottom_region, 
                                 confidence_threshold=0.5,
                                 debug_save=debug_dir / "02_search_plus.png")
    
    if result:
        x, y, w, h = result
        click_x = x + w // 2
        click_y = y + h // 2
        plus_position = (click_x, click_y)  # Save position for Step 5
        log.info(f"  ✓ Found '+' button at ({click_x}, {click_y})")
        ag.click(click_x, click_y)
        time.sleep(1.5)
        plus_clicked = True
        ag.screenshot(str(debug_dir / "02_plus_clicked_ocr.png"))
    
    if not plus_clicked:
        log.warning("  Could not find '+' button by OCR, using fallback coordinates")
        plus_btn_x = wl + int(ww * 0.065)
        plus_btn_y = wt + wh - int(wh * 0.052)
        plus_position = (plus_btn_x, plus_btn_y)
        ag.click(plus_btn_x, plus_btn_y)
        time.sleep(1.5)
        ag.screenshot(str(debug_dir / "02_plus_clicked_fallback.png"))
    
    # Move cursor to center of screen to avoid interfering with file picker
    log.info("  Moving cursor to center of screen...")
    center_x = wl + ww // 2
    center_y = wt + wh // 2
    ag.moveTo(center_x, center_y, duration=0.3)
    time.sleep(0.5)
    
    if not plus_clicked and not plus_position:
        log.error("✗ Step 2 FAILED: Could not click '+' button")
        return False
    
    # ── Step 3: Navigate Windows file picker ───────────────────────────────────
    log.info("Step 3: Typing full file path in Windows picker...")
    time.sleep(1)
    # Type the full file path directly
    ag.typewrite(str(md_path.absolute()), interval=0.03)
    time.sleep(0.5)
    ag.press("enter")
    time.sleep(2)  # Wait for file to be added to list
    ag.screenshot(str(debug_dir / "03_file_added.png"))
    
    # ── Step 4: Find and double-click the file using OCR ───────────────────────
    log.info("Step 4: Finding file '%s' in list using OCR...", md_path.stem)
    
    # Define the file list region (entire left panel, not just bottom)
    list_region = (wl, wt, int(ww * 0.25), wh)  # Left 25% of window, full height
    
    # Try to find the file name with multiple strategies
    search_terms = [
        md_path.stem,                          # Full name: "Abastar"
        md_path.stem[:len(md_path.stem)//2],  # First half: "Abas"
        md_path.stem[:4] if len(md_path.stem) >= 4 else md_path.stem[:3]  # First 4 or 3 chars
    ]
    
    result = None
    found_term = None
    file_loaded = False
    
    for term in search_terms:
        if len(term) < 3:  # Skip if too short
            continue
        log.info(f"  Searching for '{term}' in left panel...")
        result = find_text_on_screen(term, region=list_region, 
                                     confidence_threshold=0.5,  # Lower threshold
                                     debug_save=debug_dir / f"04_search_{term}.png")
        if result:
            found_term = term
            break
    
    if result:
        x, y, w, h = result
        # Double-click in the center of the found text
        click_x = x + w // 2
        click_y = y + h // 2
        log.info(f"  ✓ Found '{found_term}' at ({click_x}, {click_y})")
        log.info(f"  Text bounding box: x={x}, y={y}, width={w}, height={h}")
        log.info(f"  Double-clicking at center: ({click_x}, {click_y})")
        
        # Ensure window is active
        win.activate()
        time.sleep(0.3)
        
        # Move to position first
        ag.moveTo(click_x, click_y, duration=0.3)
        time.sleep(0.3)
        ag.screenshot(str(debug_dir / "04a_before_doubleclick.png"))
        
        # Perform double-click with explicit clicks (more reliable than doubleClick)
        ag.click(click_x, click_y)
        time.sleep(0.1)  # Short delay between clicks
        ag.click(click_x, click_y)
        log.info(f"  Executed two clicks at ({click_x}, {click_y})")
        
        time.sleep(2)  # Wait for file to load
        ag.screenshot(str(debug_dir / "04_file_loaded_ocr.png"))
        file_loaded = True
        log.info(f"  ✓ Double-clicked on '{found_term}' successfully")
    else:
        log.warning(f"  Could not find '{md_path.stem}' by OCR, using fallback")
        # Fallback: use keyboard navigation
        list_cx = wl + int(ww * 0.065)
        list_cy = wt + wh - int(wh * 0.17)
        ag.click(list_cx, list_cy)
        time.sleep(0.5)
        ag.press("end")
        time.sleep(0.5)
        ag.doubleClick(list_cx, list_cy)
        time.sleep(2)
        ag.screenshot(str(debug_dir / "04_file_loaded_fallback.png"))
        file_loaded = True  # Assume fallback worked
    
    if not file_loaded:
        log.error(f"✗ Step 4 FAILED: Could not load file '{md_path.stem}'")
        return False
    
    # Move cursor to right side after loading file
    log.info("  Moving cursor to right side of panel...")
    right_side_x = wl + int(ww * 0.20)
    right_side_y = wt + wh - int(wh * 0.052)
    ag.moveTo(right_side_x, right_side_y, duration=0.3)
    time.sleep(0.5)
    ag.screenshot(str(debug_dir / "04b_cursor_moved_right.png"))

    # ── Step 5: Find export icon on the EXTREME RIGHT using OpenCV ─────────────
    log.info("Step 5: Searching for export icon on the EXTREME RIGHT using OpenCV...")
    
    export_pos = None
    export_success = False
    
    # Focus search on the EXTREME RIGHT of the left panel toolbar
    # The export button is at the far right edge
    panel_width = int(ww * 0.25)  # Left panel is ~25% of window
    right_region = (
        wl + int(panel_width * 0.7),  # Start at 70% of panel width (rightmost area)
        wt + int(wh * 0.88),           # Bottom toolbar area
        int(panel_width * 0.3),        # Search the rightmost 30% of panel
        int(wh * 0.12)                 # Height of toolbar
    )
    
    log.info(f"  Searching in extreme right region: x={right_region[0]}, y={right_region[1]}, w={right_region[2]}, h={right_region[3]}")
    
    # Try OpenCV detection in the extreme right region
    if OPENCV_AVAILABLE:
        try:
            import cv2
            
            # Capture the right side of toolbar
            screenshot = ag.screenshot(region=right_region)
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            cv2.imwrite(str(debug_dir / "05_right_toolbar_opencv.png"), img)
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150)
            cv2.imwrite(str(debug_dir / "05_right_toolbar_edges.png"), edges)
            
            # Find contours (potential buttons/icons)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter for icon-sized contours
            icon_candidates = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                area = cv2.contourArea(cnt)
                # Icons are typically 15-40 pixels, roughly square
                if 150 < area < 1600 and 0.6 < w/h < 1.5:
                    icon_candidates.append((x, y, w, h, area))
            
            if icon_candidates:
                # Sort by area (largest icon is likely the export button)
                icon_candidates.sort(key=lambda ic: ic[4], reverse=True)
                
                # Take the largest icon as export button
                x, y, w, h, area = icon_candidates[0]
                
                # Convert back to screen coordinates
                export_x = right_region[0] + x + w // 2
                export_y = right_region[1] + y + h // 2
                
                log.info(f"  ✓ OpenCV found {len(icon_candidates)} icons on right, using largest at ({export_x}, {export_y})")
                export_pos = (export_x, export_y)
                
                # Draw rectangles on debug image
                for ix, iy, iw, ih, _ in icon_candidates:
                    cv2.rectangle(img, (ix, iy), (ix + iw, iy + ih), (0, 255, 0), 2)
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 3)  # Highlight selected
                cv2.imwrite(str(debug_dir / "05_right_icons_detected.png"), img)
            else:
                log.warning("  No icon candidates found on right side by OpenCV")
        except Exception as e:
            log.warning(f"  OpenCV detection failed: {e}")
    
    # Try template matching if OpenCV detection didn't work
    if not export_pos:
        export_icon_path = Path(__file__).parent / "icons" / "export_icon.png"
        
        if export_icon_path.exists():
            try:
                log.info(f"  Trying template matching with: {export_icon_path}")
                # Search only in the right region
                icon_location = ag.locateOnScreen(str(export_icon_path), region=right_region, confidence=0.7)
                
                if icon_location:
                    export_pos = ag.center(icon_location)
                    log.info(f"  ✓ Template matching found export icon at {export_pos}")
            except Exception as e:
                log.warning(f"  Template matching failed: {e}")
    
    # Use the found position or fallback
    if export_pos:
        export_btn_x, export_btn_y = export_pos
        log.info(f"  Clicking export button at ({export_btn_x}, {export_btn_y})")
        ag.click(export_btn_x, export_btn_y)
        time.sleep(CFG["ui_delay"] * 2)
        ag.screenshot(str(debug_dir / "05_export_clicked_opencv.png"))
        export_success = True
    else:
        # Fallback: use absolute position at the FAR RIGHT of left panel
        panel_width = int(ww * 0.25)
        # Export button is at the extreme right, near the edge
        export_btn_x = wl + panel_width - 40  # 40 pixels from right edge
        export_btn_y = wt + wh - int(wh * 0.052)  # Same Y as other buttons
        log.info(f"  Using fallback (extreme right of panel): ({export_btn_x}, {export_btn_y})")
        log.info(f"  Panel extends from {wl} to {wl + panel_width}, clicking at {export_btn_x}")
        
        ag.click(export_btn_x, export_btn_y)
        time.sleep(CFG["ui_delay"] * 2)
        ag.screenshot(str(debug_dir / "05_export_clicked_fallback.png"))
        export_success = True  # Assume fallback worked
    
    if not export_success:
        log.error("✗ Step 5 FAILED: Could not click export button")
        return False
    
    # ── Step 6: Handle export dialog with OCR ──────────────────────────────────
    log.info("Step 6: Filling export dialog with OCR...")
    time.sleep(1)
    handle_export_dialog_ocr(win, fbx_path)
    
    # Wait for export to complete
    log.info("Waiting for export to complete...")
    time.sleep(5)
    
    # Check if FBX was created in MotionFiles folder
    motion_files_fbx = Path("MotionFiles") / fbx_path.name
    if motion_files_fbx.exists():
        log.info("Moving FBX from MotionFiles to output directory...")
        fbx_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(motion_files_fbx), str(fbx_path))
        log.info(f"✓ FBX file created: {fbx_path}")
        return True
    elif fbx_path.exists():
        log.info(f"✓ FBX file created: {fbx_path}")
        return True
    else:
        log.error("✗ FBX file not found after export")
        return False


def main():
    parser = argparse.ArgumentParser(description="Convert mHand .md files to FBX using OCR")
    parser.add_argument("--input", "-i", required=True, help="Input .md file")
    parser.add_argument("--output", "-o", help="Output .fbx file (optional)")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR, use legacy method")
    args = parser.parse_args()
    
    # Check dependencies
    if not args.no_ocr:
        if not check_tesseract_installation():
            log.error("Tesseract OCR not installed!")
            log.error("Download from: https://github.com/UB-Mannheim/tesseract/wiki")
            log.error("Or run with --no-ocr to use legacy coordinate-based method")
            sys.exit(1)
    
    md_path = Path(args.input)
    if not md_path.exists():
        log.error("Input file not found: %s", md_path)
        sys.exit(1)
    
    # Determine output path
    if args.output:
        fbx_path = Path(args.output)
    else:
        output_dir = Path(CFG["output_dir"]) if CFG["output_dir"] else md_path.parent
        output_dir.mkdir(exist_ok=True)
        fbx_path = output_dir / f"{md_path.stem}.fbx"
    
    log.info("=" * 70)
    log.info("mHand → FBX Converter (OCR-Enhanced)")
    log.info("=" * 70)
    log.info("Input:  %s", md_path)
    log.info("Output: %s", fbx_path)
    log.info("OCR:    %s", "Enabled" if not args.no_ocr else "Disabled")
    log.info("=" * 70)
    
    if args.no_ocr:
        log.warning("OCR disabled - using legacy method")
        # Import and use original method
        from mhand_to_fbx import export_fbx_via_ui
        success = export_fbx_via_ui(md_path, fbx_path)
    else:
        success = export_fbx_via_ui_ocr(md_path, fbx_path)
    
    if success:
        log.info("✓ Conversion completed successfully")
        return 0
    else:
        log.error("✗ Conversion failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
