"""Claude-based image analysis for privacy risks."""

import anthropic
import base64
import json
import re
from typing import Dict, Any, Tuple
from PIL import Image
import io

from prompts import ANALYSIS_PROMPT, VERIFICATION_PROMPT
from text_detector import get_detector
from risk import calculate_risk


def get_image_media_type(image_bytes: bytes) -> str:
    """Detect image media type from bytes."""
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif image_bytes[:2] == b'\xff\xd8':
        return "image/jpeg"
    elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    else:
        return "image/jpeg"


def parse_claude_response(response_text: str) -> Dict[str, Any]:
    """Parse Claude's JSON response, handling potential formatting issues."""
    # Try direct JSON parse first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in text
    json_match = re.search(r'\{.*"findings".*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return {"findings": []}


def estimate_bbox_from_hint(region_hint: str, image_size: Tuple[int, int]) -> Dict[str, int]:
    """Create an approximate bounding box from a region hint."""
    width, height = image_size
    hint = region_hint.lower()

    region_w = int(width * 0.2)
    region_h = int(height * 0.15)

    if "left" in hint:
        x = int(width * 0.1)
    elif "right" in hint:
        x = int(width * 0.7)
    else:
        x = int(width * 0.4)

    if "top" in hint or "upper" in hint:
        y = int(height * 0.1)
    elif "bottom" in hint or "lower" in hint:
        y = int(height * 0.75)
    else:
        y = int(height * 0.4)

    if "center" in hint or "middle" in hint:
        x = int(width * 0.4)
        y = int(height * 0.4)

    if "corner" in hint:
        region_w = int(width * 0.25)
        region_h = int(height * 0.2)

    return {"x": x, "y": y, "w": region_w, "h": region_h}


def analyze_image_sync(image_bytes: bytes, client: anthropic.Anthropic) -> Dict[str, Any]:
    """Analyze an image for privacy risks using Claude (synchronous)."""
    media_type = get_image_media_type(image_bytes)
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    pil_image = Image.open(io.BytesIO(image_bytes))
    image_size = pil_image.size

    # Call Claude for analysis
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT
                    }
                ],
            }
        ],
    )

    response_text = response.content[0].text
    result = parse_claude_response(response_text)
    findings = result.get("findings", [])

    # Run EasyOCR to get precise text regions
    if findings:
        try:
            detector = get_detector()
            text_regions = detector.detect_text_regions(image_bytes)

            for finding in findings:
                if finding.get("has_text", False):
                    bbox = detector.match_finding_to_text(finding, text_regions, image_size)
                    if bbox:
                        finding["bbox"] = bbox
                    else:
                        finding["bbox"] = estimate_bbox_from_hint(finding.get("region_hint", ""), image_size)
                else:
                    finding["bbox"] = estimate_bbox_from_hint(finding.get("region_hint", ""), image_size)
        except Exception as e:
            print(f"OCR failed: {e}")
            for finding in findings:
                finding["bbox"] = estimate_bbox_from_hint(finding.get("region_hint", ""), image_size)

    risk_score = calculate_risk(findings)

    return {
        "findings": findings,
        "risk_score": risk_score,
        "image_size": {"width": image_size[0], "height": image_size[1]}
    }


def verify_protection_sync(image_bytes: bytes, client: anthropic.Anthropic) -> Dict[str, Any]:
    """Verify a protected image by running a blind analysis (synchronous)."""
    media_type = get_image_media_type(image_bytes)
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": VERIFICATION_PROMPT
                    }
                ],
            }
        ],
    )

    response_text = response.content[0].text
    result = parse_claude_response(response_text)
    findings = result.get("findings", [])

    risk_score = calculate_risk(findings)

    return {
        "residual_risks": findings,
        "risk_score": risk_score
    }
