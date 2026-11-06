"""Image protection: erase regions smoothly and strip metadata."""

import cv2
import numpy as np
from PIL import Image
import io
from typing import List, Dict, Any, Tuple


def erase_region(
    image: np.ndarray,
    bbox: Dict[str, int],
    padding: int = 3
) -> np.ndarray:
    """
    Smoothly erase a region using inpainting.

    Args:
        image: OpenCV image (BGR format)
        bbox: {"x": int, "y": int, "w": int, "h": int}
        padding: Extra pixels around the region

    Returns:
        Image with erased region
    """
    height, width = image.shape[:2]

    # Extract coordinates with padding
    x = max(0, bbox["x"] - padding)
    y = max(0, bbox["y"] - padding)
    w = min(width - x, bbox["w"] + 2 * padding)
    h = min(height - y, bbox["h"] + 2 * padding)

    if w <= 0 or h <= 0:
        return image

    # Create mask for inpainting
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[y:y+h, x:x+w] = 255

    # Use inpainting to fill the region smoothly
    # INPAINT_TELEA is good for small regions
    result = cv2.inpaint(image, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)

    return result


def strip_metadata(image: Image.Image) -> Image.Image:
    """Remove all EXIF metadata from an image."""
    data = list(image.getdata())
    mode = image.mode
    size = image.size

    clean_image = Image.new(mode, size)
    clean_image.putdata(data)

    return clean_image


def protect_image(
    image_bytes: bytes,
    findings: List[Dict[str, Any]],
    fix_ids: List[int]
) -> Tuple[bytes, List[Dict[str, Any]]]:
    """
    Apply protection to an image by erasing selected regions.

    Args:
        image_bytes: Original image as bytes
        findings: List of findings with bboxes
        fix_ids: IDs of findings to fix

    Returns:
        Tuple of (protected image bytes, list of applied fixes)
    """
    pil_image = Image.open(io.BytesIO(image_bytes))

    if pil_image.mode in ('RGBA', 'P'):
        pil_image = pil_image.convert('RGB')

    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    applied_fixes = []

    # Erase each selected finding
    for finding in findings:
        if finding.get("id") in fix_ids:
            bbox = finding.get("bbox")
            if bbox:
                cv_image = erase_region(cv_image, bbox)
                applied_fixes.append({
                    "id": finding["id"],
                    "description": finding.get("description", ""),
                    "action": "erased"
                })

    result_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
    result_image = strip_metadata(result_image)

    buffer = io.BytesIO()
    result_image.save(buffer, format='JPEG', quality=95)

    return buffer.getvalue(), applied_fixes


def create_annotated_image(
    image_bytes: bytes,
    findings: List[Dict[str, Any]]
) -> bytes:
    """Create an annotated image with numbered markers on findings."""
    pil_image = Image.open(io.BytesIO(image_bytes))

    if pil_image.mode in ('RGBA', 'P'):
        pil_image = pil_image.convert('RGB')

    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    for finding in findings:
        bbox = finding.get("bbox")
        if not bbox:
            continue

        finding_id = finding.get("id", 0)
        severity = finding.get("severity", "medium")

        colors = {
            "high": (0, 0, 255),      # Red
            "medium": (0, 165, 255),  # Orange
            "low": (0, 255, 255),     # Yellow
        }
        color = colors.get(severity, (0, 165, 255))

        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]

        # Draw rectangle with thicker border
        cv2.rectangle(cv_image, (x, y), (x + w, y + h), color, 3)

        # Draw number marker
        marker_radius = 18
        marker_x = x + w // 2
        marker_y = max(marker_radius + 5, y - 15)

        cv2.circle(cv_image, (marker_x, marker_y), marker_radius, color, -1)
        cv2.circle(cv_image, (marker_x, marker_y), marker_radius, (255, 255, 255), 2)

        # Draw number
        text = str(finding_id)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2

        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = marker_x - text_size[0] // 2
        text_y = marker_y + text_size[1] // 2

        cv2.putText(cv_image, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)

    result_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
    buffer = io.BytesIO()
    result_image.save(buffer, format='JPEG', quality=95)

    return buffer.getvalue()
