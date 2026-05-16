# 🚀 Quick Start: OCR-Enhanced Automation

## What's New?

Your automation script now supports **AI-powered click detection** using Tesseract OCR! Instead of clicking at hardcoded coordinates, it intelligently finds UI elements by reading the screen text.

## 📁 New Files Created

1. **`ocr_ui_helper.py`** - Core OCR functionality module
2. **`mhand_to_fbx_ocr.py`** - OCR-enhanced version of the main script
3. **`test_ocr_setup.py`** - Test suite to verify OCR is working
4. **`OCR_SETUP.md`** - Complete installation & usage guide
5. **`requirements.txt`** - Updated with OCR dependencies

## 🎯 Quick Setup (3 Steps)

### Step 1: Install Tesseract OCR

**Download:** https://github.com/UB-Mannheim/tesseract/wiki

- Get: `tesseract-ocr-w64-setup-5.3.x.exe`
- ✅ Check "Add to PATH" during installation
- Default path: `C:\Program Files\Tesseract-OCR\`

### Step 2: Install Python Dependencies

```powershell
cd C:\Users\Locatech\automacao_mhand\mHandStudio_fbx_conversion
pip install -r requirements.txt
```

### Step 3: Test OCR Setup

```powershell
# Verify Tesseract
tesseract --version

# Run test suite
python test_ocr_setup.py
```

If all tests pass ✅, you're ready to go!

---

## 🎮 Usage Examples

### Convert Single File (OCR)
```powershell
python mhand_to_fbx_ocr.py --input "mao\01-05\Abastar.md"
```

### Batch Convert with OCR
Update `md_to_fbx.ps1`:
```powershell
Get-ChildItem -Path "mao\*.md" -Recurse | ForEach-Object {
    Write-Host "Processing: $($_.Name)" -ForegroundColor Cyan
    python mhand_to_fbx_ocr.py --input $_.FullName
}
```

### Fallback to Legacy Mode
If OCR fails or isn't installed:
```powershell
python mhand_to_fbx_ocr.py --input "mao\Abastar.md" --no-ocr
```

---

## ✨ Key Advantages

### Before (Legacy):
```python
# Hardcoded coordinates - breaks with different resolutions
ag.click(728, 389)  # Hope this is the OK button!
```

### After (OCR):
```python
# Intelligent text detection - works anywhere
click_button_by_text("OK")  # Finds OK button wherever it is
```

### Benefits:
- ✅ **Works on any screen resolution**
- ✅ **Adapts to DPI scaling automatically**
- ✅ **Supports English menus** (Chinese fallback)
- ✅ **Self-adjusts if UI layout changes**
- ✅ **Debug screenshots** saved automatically
- ✅ **More maintainable** - no coordinate updates needed

---

## 🐛 Troubleshooting

### "Tesseract not found"
```powershell
# Check installation
tesseract --version

# If not found, reinstall with PATH option
# Or manually set path in ocr_ui_helper.py line 15
```

### OCR Not Detecting Text
1. Check debug screenshots in `fbx/_ocr_debug/`
2. Lower confidence threshold in code
3. Use `--no-ocr` flag as fallback

### Still Having Issues?
```powershell
# Run diagnostic test
python test_ocr_setup.py

# Check debug images in _ocr_debug/ folder
# Compare with original script
python mhand_to_fbx.py --input "test.md"
```

---

## 📚 Documentation

| File | Description |
|------|-------------|
| [OCR_SETUP.md](OCR_SETUP.md) | Complete OCR installation & usage guide |
| [WIKI.md](WIKI.md) | Main documentation (updated with OCR info) |
| [ocr_ui_helper.py](ocr_ui_helper.py) | OCR module with inline documentation |
| [test_ocr_setup.py](test_ocr_setup.py) | Test suite with examples |

---

## 🎓 How OCR Works

### Detection Process:

1. **Screenshot** → Captures target window
2. **Preprocess** → Grayscale, threshold, denoise  
3. **OCR** → Tesseract reads all text on screen
4. **Search** → Finds target text (e.g., "Export", "OK")
5. **Calculate** → Gets click coordinates from text position
6. **Click** → Clicks center of detected element

### Example: Finding "FBX binary" Option

```python
# Traditional way (fragile)
ag.click(728, 267)  # Position 4 in dropdown

# OCR way (robust)
smart_dropdown_select("Export Type", "FBX binary")
# Automatically finds dropdown and selects option
```

---

## 🔄 Migration Path

You can use both versions side-by-side:

```
mhand_to_fbx.py        ← Legacy (always works, no setup)
mhand_to_fbx_ocr.py    ← OCR (better, needs Tesseract)
```

**Recommendation:**
1. Keep using `mhand_to_fbx.py` until OCR is fully tested
2. Install Tesseract and run `test_ocr_setup.py`
3. Try `mhand_to_fbx_ocr.py` on test files
4. Switch to OCR version when confident

---

## 🚦 Next Steps

### ✅ Immediate Actions:
1. Install Tesseract OCR
2. Run `pip install -r requirements.txt`
3. Test with `python test_ocr_setup.py`

### 🎯 Start Using:
```powershell
# Simple test
python mhand_to_fbx_ocr.py --input "mao\01-05\Abastar.md"

# Check debug images
dir fbx\_ocr_debug\
```

### 📈 Advanced (Optional):
- Customize OCR confidence thresholds
- Add support for more languages
- Create custom UI element detectors
- Implement template matching for icons

---

## ❓ Questions?

- Check debug screenshots: `fbx/_ocr_debug/` or `_ocr_debug/`
- Read full guide: [OCR_SETUP.md](OCR_SETUP.md)
- Test OCR: `python test_ocr_setup.py`
- Compare with legacy: `python mhand_to_fbx.py --input test.md`

**Happy Automating!** 🎉
