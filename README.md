# Pinpoint

**Visual Privacy Protection Tool**

Pinpoint analyzes images for privacy risks using AI vision, lets you erase sensitive information, and applies cloaking to protect against facial recognition.

## Features

### 1. Privacy Risk Detection
Uses Claude AI to identify visible privacy risks:
- **ID Cards/Badges** - Employee IDs, access cards, even partially visible
- **License Plates** - Vehicle registration numbers
- **House Numbers** - Residential address identifiers
- **Street Signs** - Street names that reveal location
- **Documents** - Any readable personal information

### 2. Smart Erasure
- Removes selected risks using AI inpainting (not just blur)
- Produces clean, natural-looking results
- Strips all EXIF metadata (GPS, camera info, timestamps)

### 3. Anti-AI Cloaking
- Adds invisible perturbations that disrupt facial recognition
- Enhanced protection around detected faces
- Image appears normal to humans

## Quick Start

### Prerequisites
- Python 3.9+
- Anthropic API key

### Installation

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
export ANTHROPIC_API_KEY=your_key_here
python app.py
```

Open **http://localhost:5000** in your browser.

## Usage

1. **Upload** - Drag and drop or click to select an image
2. **Review** - See detected risks with severity ratings
3. **Select** - Choose which risks to erase (all selected by default)
4. **Erase** - Click to remove selected risks
5. **Cloak** - Optionally apply anti-facial-recognition protection
6. **Download** - Save the protected image

## API Endpoints

### POST /analyze
Analyze an image for privacy risks.

**Request:**
```json
{
  "image": "<base64 encoded image>"
}
```

**Response:**
```json
{
  "findings": [
    {
      "id": 1,
      "category": "license_plate",
      "description": "License plate visible on vehicle",
      "severity": "high",
      "region_hint": "bottom left",
      "bbox": {"x": 100, "y": 200, "w": 80, "h": 30}
    }
  ],
  "risk_score": 65,
  "risk_level": "high",
  "annotated_image": "<base64>"
}
```

### POST /protect
Erase selected risks from an image.

**Request:**
```json
{
  "image": "<base64>",
  "findings": [...],
  "fix_ids": [1, 2],
  "verify": true
}
```

**Response:**
```json
{
  "protected_image": "<base64>",
  "before_score": 65,
  "after_score": 10,
  "residual_risks": []
}
```

### POST /cloak
Apply anti-facial-recognition cloaking.

**Request:**
```json
{
  "image": "<base64>",
  "intensity": 0.04
}
```

**Response:**
```json
{
  "cloaked_image": "<base64>",
  "faces_detected": true,
  "message": "Cloaking applied with enhanced protection around detected faces"
}
```

## Risk Scoring

| Score | Level | Meaning |
|-------|-------|---------|
| 0-24 | Low (Green) | Safe to share |
| 25-59 | Medium (Amber) | Review before sharing |
| 60-100 | High (Red) | Contains identifying information |

### Risk Points by Category
- ID Card/Badge: 40 points
- License Plate: 30 points
- House Number: 30 points
- Document: 35 points
- Street Sign: 25 points
- Business Sign: 15 points

## Project Structure

```
pinpoint/
├── backend/
│   ├── app.py              # Flask application
│   ├── analyzer.py         # Claude vision analysis
│   ├── protector.py        # Inpainting & metadata removal
│   ├── cloaker.py          # Anti-AI cloaking
│   ├── text_detector.py    # EasyOCR integration
│   ├── prompts.py          # Claude prompts
│   ├── risk.py             # Risk scoring
│   ├── requirements.txt
│   └── templates/
│       └── index.html      # Web UI
└── README.md
```

## Tech Stack

- **Backend**: Flask (Python)
- **AI Analysis**: Claude API (Anthropic)
- **Text Detection**: EasyOCR
- **Image Processing**: OpenCV, Pillow
- **Frontend**: HTML, Tailwind CSS, Vanilla JS

## Privacy & Security

- Images are processed on-demand and not stored
- All EXIF metadata is stripped from output images
- API key is required for Claude access
- No external tracking or analytics

## Limitations

- Detection accuracy depends on image quality and text readability
- Cloaking provides protection but is not 100% foolproof against all AI systems
- Processing time depends on image size and server resources
- EasyOCR runs on CPU (slower than GPU but more portable)

## License

MIT
