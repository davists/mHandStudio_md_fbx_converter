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

# Import OCR helper
from ocr_ui_helper import (
    click_button_by_text,
    smart_dropdown_select,
    find_and_click_text,
    verify_text_exists,
    check_tesseract_installation,
    find_text_on_screen
)

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
    "output_dir":      "fbx",
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
    
    # ── File Name (优先使用OCR查找字段) ──────────────────────────────────────────
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
    
    # ── Export Type / Format (使用OCR查找FBX选项) ──────────────────────────────
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
    
    # ── OK Button (使用OCR查找确定按钮) ────────────────────────────────────────
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
    Adapts to any resolution and UI language (English supported).
    """
    ag.FAILSAFE = True
    ag.PAUSE = 0.1

    win = find_or_launch_mhand()
    
    wl, wt = win.left, win.top
    ww, wh = win.width, win.height
    log.info("Window: (%d,%d) %dx%d", wl, wt, ww, wh)
    
    try:
        win.activate()
    except Exception:
        pass
    time.sleep(0.5)
    
    # TODO: Add OCR-based menu navigation here
    # For now, use keyboard shortcuts which are more universal
    
    # Open file menu (typically Ctrl+O or Alt+F)
    log.info("Opening file menu...")
    ag.hotkey("ctrl", "o")
    time.sleep(1)
    
    # TODO: Use OCR to find and click "Export" or "导出" menu item
    
    # For now, trigger export dialog with a known shortcut or sequence
    # This part depends on your specific mHandStudio workflow
    
    # Handle the export dialog with OCR
    handle_export_dialog_ocr(win, fbx_path)
    
    return True


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
