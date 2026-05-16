# OCR-Enhanced UI Automation Setup

## Overview

The OCR-enhanced version uses **Tesseract OCR** and **Computer Vision** to intelligently locate UI elements by reading screen text, making the automation:

- ✅ **Resolution-independent** - Works on any screen size or DPI setting
- ✅ **Language-aware** - Supports English menus (can be extended to other languages)
- ✅ **Self-adjusting** - Finds buttons/dropdowns even if UI layout changes slightly
- ✅ **More reliable** - Less dependent on exact pixel coordinates

---

## Installation Steps

### 1. Install Tesseract OCR

#### Windows:
Download and install from GitHub:
```
https://github.com/UB-Mannheim/tesseract/wiki
```

**Recommended installer:** `tesseract-ocr-w64-setup-5.3.x.exe`

**Default installation path:** `C:\Program Files\Tesseract-OCR\tesseract.exe`

During installation:
- ✅ Check "Add to PATH" option
- ✅ Install English language data (eng.traineddata)

#### Verify Installation:
Open PowerShell and run:
```powershell
tesseract --version
```

You should see version information like:
```
tesseract v5.3.0.20221222
```

---

### 2. Install Python Dependencies

Navigate to the project directory and install requirements:

```powershell
cd C:\Users\Locatech\automacao_mhand\mHandStudio_fbx_conversion
pip install -r requirements.txt
```

This installs:
- `opencv-python` - Image processing
- `pytesseract` - Python wrapper for Tesseract
- `numpy` - Numerical operations
- `Pillow` - Image handling
- (existing dependencies)

---

### 3. Configure Tesseract Path (if needed)

If Tesseract is installed in a non-standard location, edit [ocr_ui_helper.py](ocr_ui_helper.py):

```python
# Line ~15
TESSERACT_PATH = r"C:\Your\Custom\Path\tesseract.exe"
```

---

## Usage

### Basic Usage (OCR-enabled):

```powershell
python mhand_to_fbx_ocr.py --input "mao/01-05/Abastar.md"
```

### Disable OCR (fallback to legacy method):

```powershell
python mhand_to_fbx_ocr.py --input "mao/01-05/Abastar.md" --no-ocr
```

### Batch Processing:

Update [md_to_fbx.ps1](md_to_fbx.ps1) to use OCR version:

```powershell
Get-ChildItem -Path "mao\*.md" -Recurse | ForEach-Object {
    Write-Host "Processing: $($_.Name)" -ForegroundColor Cyan
    python mhand_to_fbx_ocr.py --input $_.FullName
}
```

---

## How It Works

### OCR Text Detection

Instead of clicking at hardcoded coordinates like `(728, 267)`, the script:

1. **Captures screenshot** of the target window
2. **Preprocesses image** (grayscale, threshold, denoise)
3. **Runs Tesseract OCR** to detect all text on screen
4. **Searches for target text** (e.g., "Export", "OK", "FBX binary")
5. **Calculates click position** based on detected text location
6. **Clicks intelligently** at the center of the found element

### Example: Finding "OK" Button

**Legacy method (fragile):**
```python
ag.click(728, 389)  # Hope this is the OK button!
```

**OCR method (robust):**
```python
click_button_by_text("OK")  # Finds OK button wherever it is
```

---

## Debugging

### Enable Debug Screenshots

Debug images are automatically saved to `fbx/_ocr_debug/` folder showing:

- What text was detected
- Where the script clicked
- Confidence levels
- Failed searches

### Test OCR Installation

Run the OCR helper directly:

```powershell
python ocr_ui_helper.py
```

This will:
- Check Tesseract installation
- Capture your screen
- Try to find common UI text like "Start", "File", "Edit"

---

## Supported Languages

Currently configured for **English** menus with fallback to **Chinese**.

### To Add More Languages:

1. Download language data from Tesseract:
   ```
   https://github.com/tesseract-ocr/tessdata
   ```

2. Place `.traineddata` files in:
   ```
   C:\Program Files\Tesseract-OCR\tessdata\
   ```

3. Update OCR calls to use multiple languages:
   ```python
   pytesseract.image_to_data(image, lang='eng+por')  # English + Portuguese
   ```

---

## Advantages Over Legacy Method

| Feature | Legacy Method | OCR Method |
|---------|--------------|------------|
| **Resolution** | Hardcoded for specific resolution | Works on any resolution |
| **DPI Scaling** | Breaks with different DPI settings | DPI-independent |
| **UI Changes** | Breaks if UI layout changes | Self-adjusting |
| **Multi-language** | Separate code per language | Searches for text in any language |
| **Debugging** | Hard to diagnose failures | Visual debug screenshots |
| **Maintenance** | Need to update coordinates manually | Minimal maintenance |

---

## Troubleshooting

### "Tesseract not found" Error

**Problem:** `TesseractNotFoundError`

**Solutions:**
1. Verify installation: `tesseract --version`
2. Check path in `ocr_ui_helper.py`
3. Reinstall Tesseract with "Add to PATH" option

### Text Not Detected

**Problem:** OCR fails to find buttons/text

**Solutions:**
1. Check debug screenshots in `fbx/_ocr_debug/`
2. Adjust `confidence_threshold` (lower = more lenient)
3. Try alternative text labels:
   ```python
   # Instead of just "OK"
   ok_texts = ["OK", "确定", "Confirm", "Apply"]
   ```

### Wrong Element Clicked

**Problem:** Script clicks wrong location

**Solutions:**
1. Limit search region to specific window area:
   ```python
   find_and_click_text("Export", region=(x, y, width, height))
   ```
2. Add offset to click position:
   ```python
   find_and_click_text("Export", offset_x=50, offset_y=0)
   ```

### Performance Issues

**Problem:** OCR is slow

**Solutions:**
1. Limit search regions to smaller areas
2. Lower image resolution for preprocessing
3. Use keyboard shortcuts instead of OCR where possible

---

## Performance Tips

1. **Hybrid Approach**: Use OCR for complex dialogs, keyboard shortcuts for simple actions
2. **Cache Window Positions**: Don't re-scan for static elements
3. **Timeout Limits**: Set reasonable timeouts for text detection
4. **Region of Interest**: Always limit OCR to relevant screen areas

---

## Advanced Features

### Template Matching (Alternative to OCR)

For icon-based buttons (no text), use template matching:

```python
import cv2

def find_icon(template_path, screenshot):
    template = cv2.imread(template_path)
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    return max_loc if max_val > 0.8 else None
```

### AI-Based Element Detection (Future)

For even more robust detection, consider:
- **YOLO/SSD** for UI element detection
- **EasyOCR** as alternative to Tesseract
- **Selenium/Playwright** for web-based UIs

---

## License & Credits

- **Tesseract OCR**: Apache 2.0 License
- **OpenCV**: Apache 2.0 License
- **PyAutoGUI**: BSD License

---

## Support

For issues or questions:
1. Check debug screenshots in `_ocr_debug` folder
2. Run `python ocr_ui_helper.py` to test OCR installation
3. Try with `--no-ocr` flag to compare with legacy method
4. Review Tesseract documentation: https://tesseract-ocr.github.io/
