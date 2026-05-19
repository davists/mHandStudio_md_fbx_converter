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
    check_tesseract_installation,
    find_text_on_screen,
    handle_auto_update_dialog
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
            
            # Verificar e tratar diálogo de Auto Update logo no início
            log.info("Verificando se há diálogo de Auto Update...")
            wl, wt, ww, wh = wins[0].left, wins[0].top, wins[0].width, wins[0].height
            window_region = (wl, wt, ww, wh)
            
            # Criar diretório de debug temporário
            # temp_debug = Path.cwd() / "_startup_debug"
            # temp_debug.mkdir(exist_ok=True)
            
            # Tentar tratar o diálogo de update
            # handle_auto_update_dialog(window_region=window_region, debug_dir=temp_debug)
            
            return wins[0]

    log.error("Timeout: mHand Studio não abriu em %ds.", CFG["startup_timeout"])
    sys.exit(1)


def find_export_button_opencv(win, plus_position, debug_dir):
    """
    Use OpenCV to find the export button in the BOTTOM RIGHT corner of the viewport.
    The export icon is located in the lower right area of the 3D viewport, not in the left panel.
    Returns (x, y) position of export button, or None if not found.
    """
    if not OPENCV_AVAILABLE:
        return None
    
    try:
        import cv2
        
        wl, wt = win.left, win.top
        ww, wh = win.width, win.height
        
        # Capture the BOTTOM RIGHT corner of the window (where export icon is)
        # Search area: rightmost 15% of width, bottom 15% of height
        region_width = int(ww * 0.15)
        region_height = int(wh * 0.15)
        toolbar_region = (
            wl + ww - region_width,  # Start from right edge
            wt + wh - region_height,  # Start from bottom edge
            region_width,
            region_height
        )
        
        log.info(f"  Searching for export icon in bottom-right: x={toolbar_region[0]}, y={toolbar_region[1]}, w={region_width}, h={region_height}")
        screenshot = ag.screenshot(region=toolbar_region)
        
        # Convert PIL image to OpenCV format
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Save debug image
        cv2.imwrite(str(debug_dir / "05_bottom_right_opencv.png"), img)
        
        # Detect edges to find button outlines
        edges = cv2.Canny(gray, 50, 150)
        cv2.imwrite(str(debug_dir / "05_bottom_right_edges.png"), edges)
        
        # Find contours (potential buttons/icons)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size (icons are typically 20-50 pixels)
        button_candidates = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            # Filter: reasonable size for an icon
            if 200 < area < 3000 and 0.5 < w/h < 2.0:
                button_candidates.append((x, y, w, h))
        
        if not button_candidates:
            log.warning("  No icon candidates found in bottom-right by OpenCV")
            return None
        
        # Sort by X position (left to right), take the rightmost one
        button_candidates.sort(key=lambda b: b[0])
        
        if button_candidates:
            # Take the rightmost icon as export button
            rightmost = button_candidates[-1]
            x, y, w, h = rightmost
            
            # Convert back to screen coordinates
            export_x = toolbar_region[0] + x + w // 2
            export_y = toolbar_region[1] + y + h // 2
            
            log.info(f"  ✓ OpenCV found {len(button_candidates)} icons in bottom-right, using rightmost at ({export_x}, {export_y})")
            
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
    
    # Create debug directory at project root
    project_root = Path.cwd()
    debug_dir = project_root / "_ocr_debug"
    debug_dir.mkdir(exist_ok=True)
    log.info(f"Debug screenshots will be saved to: {debug_dir}")
    
    # Screenshot initial state
    ag.screenshot(str(debug_dir / "01_dialog_initial.png"))
    time.sleep(0.5)
    
    # ── FIRST: Click on Biovision to open the dropdown ──────────────────────────────────
    log.info("Step 1: Localizando e clicando em 'Biovision' para abrir o dropdown...")
    
    biovision_found = False
    biovision_search_terms = [
        "Biovision",
        "BVHI",
        "BVH",
        "bvh",
    ]
    
    for term in biovision_search_terms:
        log.info(f"  Procurando '{term}'...")
        result = find_text_on_screen(term, region=None,  # Full screen search
                                     confidence_threshold=0.3,
                                     debug_save=debug_dir / f"01_search_biovision_{term}.png")
        if result:
            x, y, w, h = result
            click_x = x + w // 2
            click_y = y + h // 2
            log.info(f"  ✓ Encontrado '{term}' em ({x}, {y})")
            log.info(f"  Clicando em ({click_x}, {click_y}) para abrir dropdown...")
            ag.click(click_x, click_y)
            time.sleep(1.0)  # Wait for dropdown to open
            ag.screenshot(str(debug_dir / "01_biovision_clicked_dropdown_opened.png"))
            biovision_found = True
            break
        time.sleep(0.1)
    
    if not biovision_found:
        log.warning("  ⚠ Não foi possível encontrar 'Biovision', tentando fallback...")
        # Fallback: try clicking on "Export As" label and navigating
        export_as_result = find_text_on_screen("Export As", region=None, 
                                              confidence_threshold=0.3,
                                              debug_save=debug_dir / "01_search_export_as_fallback.png")
        if export_as_result:
            x, y, w, h = export_as_result
            click_x = x + w + 50  # Click to the right of label
            click_y = y + h // 2
            log.info(f"  Clicando no campo Export As em ({click_x}, {click_y})")
            ag.click(click_x, click_y)
            time.sleep(0.5)
    
    # ── SECOND: Select FBX binary from the opened dropdown ──────────────────────────────
    log.info("Step 2: Procurando 'FBX binary' no dropdown aberto...")
    ag.screenshot(str(debug_dir / "02_dropdown_opened.png"))
    time.sleep(0.8)  # Wait for dropdown to fully render
    
    # Try multiple search terms for FBX binary
    fbx_search_terms = [
        "FBX binary",      # Exact match
        "FBX Binary",      # Case variation
        "binary",          # Just "binary"
        "FBX",             # Just "FBX"
    ]
    
    fbx_found = False
    
    for option_text in fbx_search_terms:
        log.info(f"  Buscando '{option_text}'...")
        result = find_text_on_screen(option_text, region=None,  # Full screen
                                     confidence_threshold=0.3,
                                     debug_save=debug_dir / f"02_search_fbx_{option_text.replace(' ', '_')}.png")
        if result:
            x, y, w, h = result
            click_x = x + w // 2
            click_y = y + h // 2
            log.info(f"  ✓ Encontrado '{option_text}' em ({x}, {y}), clicando...")
            ag.click(click_x, click_y)
            time.sleep(0.8)
            ag.screenshot(str(debug_dir / "02_fbx_binary_selected.png"))
            fbx_found = True
            break
        time.sleep(0.1)
    
    if not fbx_found:
        log.warning("  ⚠ 'FBX binary' não encontrado, tentando navegação por teclado...")
        ag.press("f")  # Jump to 'F' options
        time.sleep(0.3)
        ag.press("down")  # Navigate to FBX binary
        time.sleep(0.3)
        ag.press("enter")  # Select
        time.sleep(0.3)
        ag.screenshot(str(debug_dir / "02_fbx_keyboard_selected.png"))
    
    # ── File Name (Use OCR to locate the field) ──────────────────────────────────────────
    log.info("Step 3: Setting filename: %s", fbx_path.stem)
    
    # Try to find "File Name" label
    filename_labels = ["File Name", "Filename", "Name"]
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
        log.warning("Could not find filename field by OCR, using keyboard navigation")
        # Fallback: use Tab to navigate to filename field
        ag.press("tab")
        time.sleep(0.3)
    
    # Enter filename
    ag.hotkey("ctrl", "a")
    time.sleep(0.2)
    ag.typewrite(fbx_path.stem, interval=0.04)
    time.sleep(0.3)
    ag.screenshot(str(debug_dir / "03_filename_entered.png"))
    
    # Steps 1-2 already done: Biovision clicked and FBX binary selected
    # Now verify and confirm
    
    ag.screenshot(str(debug_dir / "04_format_selected.png"))
    
    # Verify FBX was selected
    log.info("Step 4: Verifying FBX binary was selected...")
    time.sleep(0.3)
    fbx_verify = find_text_on_screen("FBX", region=None, confidence_threshold=0.3)
    if fbx_verify:
        log.info("  ✓ FBX binary successfully selected!")
    else:
        log.warning("  Could not verify FBX selection, but continuing...")
    
    ag.screenshot(str(debug_dir / "07_format_verified.png"))
    
    # ── OK Button (Use OCR to find Confirm button) ────────────────────────────────────────
    
    log.info("Step 5: Procurando botão Confirm para finalizar...")
    ag.screenshot(str(debug_dir / "08_before_confirm.png"))
    time.sleep(0.5)
    
    # Try multiple possible button texts with full screen search
    confirm_texts = ["Confirm", "OK", "Export", "Apply", "Accept"]
    ok_clicked = False
    
    for confirm_text in confirm_texts:
        log.info(f"  Procurando botão '{confirm_text}'...")
        result = find_text_on_screen(confirm_text, region=None,  # Full screen
                                     confidence_threshold=0.3,
                                     debug_save=debug_dir / f"08_search_button_{confirm_text}.png")
        if result:
            x, y, w, h = result
            click_x = x + w // 2
            click_y = y + h // 2
            log.info(f"  ✓ Encontrado botão '{confirm_text}' em ({x}, {y})")
            log.info(f"  Clicando em ({click_x}, {click_y})...")
            ag.click(click_x, click_y)
            time.sleep(1.0)
            ag.screenshot(str(debug_dir / "08_confirm_clicked.png"))
            ok_clicked = True
            break
        time.sleep(0.1)
    
    if not ok_clicked:
        log.warning("  ⚠ Não foi possível encontrar botão Confirm por OCR, tentando Enter...")
        ag.press("enter")
        time.sleep(0.5)
        ag.screenshot(str(debug_dir / "08_enter_pressed.png"))
    
    ag.screenshot(str(debug_dir / "09_dialog_closed.png"))
    time.sleep(CFG["ui_delay"] * 2)
    
    log.info("✓ Export dialog completed using OCR")


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
    
    # Create debug directory at project root
    project_root = Path.cwd()
    debug_dir = project_root / "_ocr_debug"
    debug_dir.mkdir(exist_ok=True)
    log.info(f"Debug screenshots will be saved to: {debug_dir}")
    
    # Wait for interface to load
    log.info("Waiting for interface to load...")
    time.sleep(3)
    ag.screenshot(str(debug_dir / "00_initial.png"))
    
    # Handle Auto Update dialog if it appears
    window_region = (wl, wt, ww, wh)
    # handle_auto_update_dialog(window_region=window_region, debug_dir=debug_dir)
    
    # ── Pre-Step: Verificar se há diálogo de Update antes de continuar ────────
    # log.info("Pre-Step: Verificando se há diálogo de Update na tela...")
    
    # # Procurar por "Update" e "Cancel" simultaneamente
    # update_found = find_text_on_screen("Update", region=window_region, 
    #                                   confidence_threshold=0.4,
    #                                   debug_save=debug_dir / "00a_check_update.png")
    # cancel_found = find_text_on_screen("Cancel", region=window_region, 
    #                                   confidence_threshold=0.4,
    #                                   debug_save=debug_dir / "00a_check_cancel.png")
    
    # if update_found and cancel_found:
    #     log.info("  ✓ Diálogo de Update detectado (Update + Cancel presentes)")
    #     log.info("  Clicando em Cancel para fechar o diálogo...")
        
    #     # Clicar no botão Cancel
    #     cx, cy, cw, ch = cancel_found
    #     click_x = cx + cw // 2
    #     click_y = cy + ch // 2
    #     ag.click(click_x, click_y)
    #     time.sleep(2)  # Esperar o diálogo fechar
    #     ag.screenshot(str(debug_dir / "00a_update_dialog_closed.png"))
        
    #     # Verificar se o menu Edit agora está visível
    #     log.info("  Verificando se menu Edit está visível...")
    #     menu_bar_region = (wl, wt, ww, int(wh * 0.08))
        
    #     edit_visible = False
    #     for edit_label in ["Edit"]:
    #         edit_check = find_text_on_screen(edit_label, region=menu_bar_region, 
    #                                         confidence_threshold=0.6,
    #                                         debug_save=debug_dir / f"00a_check_edit_{edit_label}.png")
    #         if edit_check:
    #             log.info(f"  ✓ Menu '{edit_label}' está visível após fechar diálogo!")
    #             edit_visible = True
    #             break
        
    #     if edit_visible:
    #         log.info("  Interface pronta para uso. Continuando com o workflow...")
    #     else:
    #         log.warning("  Menu Edit não encontrado após fechar diálogo, mas continuando...")
    # else:
    #     log.info("  Nenhum diálogo de Update detectado. Continuando normalmente...")
    
    # ── Step 1: Click Edit menu using OCR ─────────────────────────────────────
    log.info("Step 1: Clicking Edit menu using OCR...")
    menu_bar_region = (wl, wt, ww, int(wh * 0.08))
    edit_labels = ["Edit"]
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
        log.error("✗ Step 1 FAILED: Could not find Edit menu")
        log.error("   Script will stop. Please ensure mHandStudio window is open and visible.")
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

    # ── Step 5: Find export icon (lower right, near + button) ───────────
    log.info("Step 5: Procurando ícone de export na região inferior direita...")
    
    export_pos = None
    export_success = False
    
    # Extract plus_position coordinates
    if plus_position:
        plus_x, plus_y = plus_position
    else:
        # Should not happen, but provide fallback
        plus_x = wl + int(ww * 0.065)
        plus_y = wt + wh - int(wh * 0.052)
    
    # O ícone de export fica próximo ao botão +, um pouco acima
    # Buscar na região inferior direita baseada na posição do +
    log.info("  Buscando na região inferior direita (perto do botão +)...")
    
    # Definir região de busca: área inferior direita, 5% acima do botão +
    search_y_offset = int(wh * 0.05)  # 5% of window height
    region_width = int(ww * 0.10)     # 10% da largura
    region_height = int(wh * 0.10)    # 10% da altura
    
    lower_right_region = (
        wl + ww - region_width,           # Lado direito
        plus_y - search_y_offset - region_height // 2,  # 5% acima do +
        region_width,
        region_height
    )
    
    log.info(f"  Região de busca (inferior direita):")
    log.info(f"    X: {lower_right_region[0]} (rightmost {region_width}px)")
    log.info(f"    Y: {lower_right_region[1]} (5% above + button at Y={plus_y})")
    log.info(f"    Width: {region_width}px, Height: {region_height}px")
    
    # Salvar screenshot da região antes de processar
    ag.screenshot(str(debug_dir / "05_search_region_preview.png"))
    
    # Try OpenCV detection in the lower-right area
    if OPENCV_AVAILABLE:
        try:
            import cv2
            
            # Capture the lower-right area
            screenshot = ag.screenshot(region=lower_right_region)
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            cv2.imwrite(str(debug_dir / "05_lower_right_opencv.png"), img)
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150)
            cv2.imwrite(str(debug_dir / "05_lower_right_edges.png"), edges)
            
            # Find contours (potential buttons/icons)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter for icon-sized contours
            icon_candidates = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                area = cv2.contourArea(cnt)
                # Icons are typically 200-3000 pixels area, roughly square/rectangular
                if 200 < area < 3000 and 0.5 < w/h < 2.0:
                    icon_candidates.append((x, y, w, h, area))
            
            if icon_candidates:
                # Sort by position: RIGHTMOST first (high X)
                icon_candidates.sort(key=lambda ic: ic[0], reverse=True)
                
                log.info(f"  ✓ OpenCV encontrou {len(icon_candidates)} ícones na região inferior direita")
                log.info(f"  Ordenação: mais à direita primeiro")
                
                # Draw rectangles on debug image
                for idx, (ix, iy, iw, ih, _) in enumerate(icon_candidates):
                    color = (0, 0, 255) if idx == 0 else (0, 255, 0)  # First icon in red, others in green
                    cv2.rectangle(img, (ix, iy), (ix + iw, iy + ih), color, 2)
                    # Add number label
                    cv2.putText(img, str(idx + 1), (ix, iy - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.imwrite(str(debug_dir / "05_lower_right_icons_detected.png"), img)
                
                # Try each icon until we find one that opens the DataExport dialog
                # Start with the rightmost icon
                for idx, (x, y, w, h, area) in enumerate(icon_candidates):
                    # Convert back to screen coordinates
                    test_x = lower_right_region[0] + x + w // 2
                    test_y = lower_right_region[1] + y + h // 2
                    
                    log.info(f"  Tentando ícone {idx + 1}/{len(icon_candidates)} em ({test_x}, {test_y})...")
                    log.info(f"    Posição relativa: X={x} (mais à direita = maior)")
                    ag.click(test_x, test_y)
                    
                    # Wait for dialog to appear and take screenshots
                    time.sleep(1.0)
                    screenshot_1s = debug_dir / f"05_icon_{idx + 1}_clicked_1s.png"
                    ag.screenshot(str(screenshot_1s))
                    log.info(f"  Screenshot salvo: {screenshot_1s.name}")
                    
                    time.sleep(1.0)
                    screenshot_2s = debug_dir / f"05_icon_{idx + 1}_clicked_2s.png"
                    ag.screenshot(str(screenshot_2s))
                    log.info(f"  Screenshot salvo: {screenshot_2s.name}")
                    
                    # Extra delay to ensure dialog is fully rendered
                    log.info(f"  Aguardando renderização completa do diálogo (mais 2.5s)...")
                    time.sleep(2.5)
                    
                    # Take final screenshot immediately before OCR
                    screenshot_final = debug_dir / f"05_icon_{idx + 1}_before_ocr.png"
                    ag.screenshot(str(screenshot_final))
                    log.info(f"  Screenshot final antes do OCR salvo: {screenshot_final.name}")
                    
                    # Check if DataExport dialog appeared
                    # Search full screen instead of just window region for better detection
                    dataexport_found = False
                    
                    log.info(f"  Procurando por textos do diálogo DataExport (tela cheia)...")
                    
                    # Try to find any text from the dialog (use lower confidence for dark UI)
                    dialog_texts = [
                        "Confirm",        # Button text - usually easy to detect
                        "Export Folder",  # First field label
                        "File Name",      # Second field label  
                        "Export As",      # Dropdown label
                        "Rotation Order", # Another field
                        "DataExport",     # Dialog title
                        "Folder",         # Part of Export Folder
                        "Name",           # Part of File Name
                    ]
                    
                    for dialog_text in dialog_texts:
                        log.info(f"    Buscando '{dialog_text}'...")
                        result = find_text_on_screen(dialog_text, region=None,  # Full screen
                                                     confidence_threshold=0.3,  # Lower threshold
                                                     debug_save=debug_dir / f"05_icon_{idx + 1}_search_{dialog_text.replace(' ', '_')}.png")
                        if result:
                            log.info(f"  ✓ Export dialog encontrado (texto '{dialog_text}') após clicar no ícone {idx + 1}!")
                            dataexport_found = True
                            break
                        time.sleep(0.1)  # Small delay between searches
                    
                    if dataexport_found:
                        export_pos = (test_x, test_y)
                        export_success = True
                        break
                    else:
                        log.info(f"  Export dialog não encontrado, tentando próximo ícone...")
                        # Press Escape to close any dialog that might have opened
                        ag.press("escape")
                        time.sleep(0.5)
                
                if not export_success:
                    log.warning("  Nenhum dos ícones detectados abriu o diálogo Export")
            else:
                log.warning("  No icon candidates found in lower-right area by OpenCV")
        except Exception as e:
            log.warning(f"  OpenCV detection failed: {e}")
    
    # If OpenCV didn't work, try fallback position
    if not export_success:
        log.info("  Trying fallback position...")
        # Fallback: calculate position based on + button (5% above, far right)
        if plus_position:
            plus_x, plus_y = plus_position
            search_y_offset = int(wh * 0.05)  # 5% of window height above +
            export_btn_x = wl + ww - 35       # 35 pixels from right edge
            export_btn_y = plus_y - search_y_offset
            log.info(f"  Using fallback (5% above + button): ({export_btn_x}, {export_btn_y})")
            log.info(f"  + button was at Y={plus_y}, export at Y={export_btn_y}")
        else:
            # Absolute fallback if + position not available
            export_btn_x = wl + ww - 35
            export_btn_y = wt + wh - int(wh * 0.15)
            log.info(f"  Using absolute fallback: ({export_btn_x}, {export_btn_y})")
        
        log.info(f"  Window: from ({wl}, {wt}) to ({wl + ww}, {wt + wh})")
        
        ag.click(export_btn_x, export_btn_y)
        
        # Wait for dialog and take screenshots
        time.sleep(1.0)
        screenshot_1s = debug_dir / "05_export_clicked_fallback_1s.png"
        ag.screenshot(str(screenshot_1s))
        log.info(f"  Screenshot salvo: {screenshot_1s.name}")
        
        time.sleep(1.0)
        screenshot_2s = debug_dir / "05_export_clicked_fallback_2s.png"
        ag.screenshot(str(screenshot_2s))
        log.info(f"  Screenshot salvo: {screenshot_2s.name}")
        
        # Extra delay to ensure dialog is fully rendered
        log.info(f"  Aguardando renderização completa do diálogo (mais 2.5s)...")
        time.sleep(2.5)
        
        # Take final screenshot immediately before OCR
        screenshot_final = debug_dir / "05_export_clicked_fallback_before_ocr.png"
        ag.screenshot(str(screenshot_final))
        log.info(f"  Screenshot final antes do OCR salvo: {screenshot_final.name}")
        
        # Check if Export dialog appeared
        # Search full screen for better detection
        dataexport_found = False
        
        log.info(f"  Procurando por textos do diálogo DataExport (tela cheia)...")
        
        dialog_texts = [
            "Confirm",
            "Export Folder",
            "File Name",
            "Export As",
            "Rotation Order",
            "DataExport",
            "Folder",
            "Name",
        ]
        
        for dialog_text in dialog_texts:
            log.info(f"    Buscando '{dialog_text}'...")
            result = find_text_on_screen(dialog_text, region=None,
                                         confidence_threshold=0.3,
                                         debug_save=debug_dir / f"05_fallback_search_{dialog_text.replace(' ', '_')}.png")
            if result:
                log.info(f"  ✓ Fallback position opened Export dialog (texto '{dialog_text}')!")
                dataexport_found = True
                export_success = True
                break
            time.sleep(0.1)
        
        if not dataexport_found:
            log.warning("  Fallback position did not open Export dialog")
    
    if not export_success:
        log.error("✗ Step 5 FAILED: Could not click export button")
        return False
    
    # ── Step 6: Handle export dialog with OCR ──────────────────────────────────
    log.info("Step 6: Filling export dialog with OCR...")
    time.sleep(1)
    handle_export_dialog_ocr(win, fbx_path)
    
    # Wait for export to complete
    log.info("Waiting for export to complete...")
    time.sleep(3)
    
    # ── Step 7: Check for "Export success" message ────────────────────────────
    log.info("Step 7: Checking for 'Export success' message...")
    
    debug_dir = Path.cwd() / "_ocr_debug"
    ag.screenshot(str(debug_dir / "10_after_export.png"))
    
    # Check if success message appeared
    success_texts = ["Export success", "success", "Success", "完成"]
    
    for text in success_texts:
        result = find_text_on_screen(text, region=None, confidence_threshold=0.4,
                                     debug_save=debug_dir / f"10_search_{text.replace(' ', '_')}.png")
        if result:
            log.info(f"✓ Export concluído com sucesso! (detectado: '{text}')")
            log.info("✓ Step 7 COMPLETE: Export success confirmed")
            return True
    
    log.info("  'Export success' não detectado, mas continuando...")
    time.sleep(2)
    
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
    args = parser.parse_args()
    
    # Check Tesseract installation
    if not check_tesseract_installation():
        log.error("Tesseract OCR not installed!")
        log.error("Download from: https://github.com/UB-Mannheim/tesseract/wiki")
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
    log.info("mHand → FBX Converter (OCR)")
    log.info("=" * 70)
    log.info("Input:  %s", md_path)
    log.info("Output: %s", fbx_path)
    log.info("=" * 70)
    
    success = export_fbx_via_ui_ocr(md_path, fbx_path)
    
    if success:
        log.info("✓ Conversion completed successfully")
        return 0
    else:
        log.error("✗ Conversion failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
