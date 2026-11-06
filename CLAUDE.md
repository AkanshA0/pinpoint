# CLAUDE.md

This file provides context for AI assistants working on the Pinpoint codebase.

## Project Overview

Pinpoint is a visual privacy protection tool that:
1. Analyzes images for privacy risks using Claude's vision API
2. Erases sensitive information using OpenCV inpainting
3. Applies anti-facial-recognition cloaking

## Architecture

```
User Browser <-> Flask App <-> Claude API
                    |
                    +-> EasyOCR (text detection)
                    +-> OpenCV (image processing)
```

## Key Files

### backend/app.py
Flask application with three main endpoints:
- `POST /analyze` - Sends image to Claude for privacy risk analysis
- `POST /protect` - Erases selected regions and strips metadata
- `POST /cloak` - Applies adversarial noise for anti-AI protection

### backend/analyzer.py
- `analyze_image_sync()` - Main analysis function
- `verify_protection_sync()` - Re-analyzes protected images for residual risks
- Uses synchronous Anthropic client (not async)
- Model: `claude-sonnet-4-6` (configurable)

### backend/prompts.py
Claude prompts for:
- `ANALYSIS_PROMPT` - Detects ID cards, plates, house numbers, street signs
- `VERIFICATION_PROMPT` - Checks if risks remain after protection

Key prompt design decisions:
- Explicitly excludes faces (never flag)
- Excludes clothing/uniforms (too many false positives)
- Prioritizes ID cards even if text not fully readable
- Distinguishes lanyard straps (ignore) from ID cards (detect)

### backend/text_detector.py
EasyOCR integration for precise bounding boxes:
- `TextDetector.detect_text_regions()` - Finds all text
- `TextDetector._classify_text()` - Categorizes as plate/house_number/street_sign
- `TextDetector.match_finding_to_text()` - Matches Claude findings to OCR regions

### backend/protector.py
Image protection:
- `erase_region()` - Uses `cv2.inpaint()` with TELEA algorithm
- `create_annotated_image()` - Draws colored boxes and numbered markers
- `strip_metadata()` - Removes all EXIF data

### backend/cloaker.py
Anti-facial-recognition:
- `cloak_image()` - Adds structured noise patterns
- `cloak_with_face_focus()` - Detects faces and applies stronger cloaking around them
- Uses Haar cascades for face detection (lightweight, no deep learning required)

### backend/risk.py
Risk scoring system:
- Points by category (id_card=40, license_plate=30, etc.)
- Severity multipliers (high=1.0, medium=0.7, low=0.4)
- Levels: low (<25), medium (25-59), high (60+)

### backend/templates/index.html
Single-page app with:
- Sections: upload, loading, results, protected, cloaked
- Vanilla JavaScript (no framework)
- Tailwind CSS via CDN

## Common Tasks

### Adding a new risk category
1. Add to `ANALYSIS_PROMPT` in `prompts.py`
2. Add points in `risk.py` RISK_POINTS dict
3. Add label in `templates/index.html` categoryLabels object
4. Optionally add classification pattern in `text_detector.py`

### Changing the Claude model
Edit `analyzer.py` line ~100 and ~162:
```python
model="claude-sonnet-4-6"
```

### Adjusting cloak intensity
Default is 0.04. Change in `app.py` cloak endpoint or pass different `intensity` from frontend.

### Adding GPU support for EasyOCR
In `text_detector.py`:
```python
self.reader = easyocr.Reader(['en'], gpu=True)
```

## Dependencies

Core:
- `flask` - Web framework
- `anthropic` - Claude API client
- `opencv-python-headless` - Image processing (no GUI)
- `pillow` - Image handling
- `easyocr` - Text detection (includes PyTorch)
- `numpy` - Array operations

EasyOCR brings in PyTorch which is large (~500MB+). This is expected.

## Environment Variables

- `ANTHROPIC_API_KEY` - Required for Claude API access

## Testing Locally

```bash
cd backend
source venv/bin/activate
export ANTHROPIC_API_KEY=sk-...
python app.py
# Open http://localhost:5000
```

## Known Issues

1. **EasyOCR CPU warning** - Normal, just means it's not using GPU
2. **PyTorch quantization warnings** - Deprecation notices, can be ignored
3. **First request slow** - EasyOCR loads models on first use (~10-15 sec)

## Code Style

- Python: Standard library style, type hints where helpful
- JavaScript: Vanilla ES6+, no build step
- HTML: Tailwind utility classes
- No linting configured (hackathon project)
