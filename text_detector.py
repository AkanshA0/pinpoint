"""EasyOCR text detection for precise text region localization."""

import easyocr
import numpy as np
import re
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
import io


class TextDetector:
    """Detects text regions in images using EasyOCR."""

    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=False)

    def detect_text_regions(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Detect all text regions in an image."""
        image = Image.open(io.BytesIO(image_bytes))
        image_np = np.array(image)

        results = self.reader.readtext(image_np)

        detections = []
        for result in results:
            bbox_points, text, confidence = result

            x_coords = [p[0] for p in bbox_points]
            y_coords = [p[1] for p in bbox_points]

            x = int(min(x_coords))
            y = int(min(y_coords))
            w = int(max(x_coords) - x)
            h = int(max(y_coords) - y)

            # Classify the text type
            text_type = self._classify_text(text)

            detections.append({
                "text": text,
                "bbox": {"x": x, "y": y, "w": w, "h": h},
                "confidence": float(confidence),
                "text_type": text_type
            })

        return detections

    def _classify_text(self, text: str) -> str:
        """Classify detected text into categories."""
        text_clean = text.strip().upper()

        # License plate pattern: mix of letters and numbers, typically 5-8 chars
        if re.match(r'^[A-Z0-9]{4,8}$', text_clean.replace(' ', '').replace('-', '')):
            if any(c.isdigit() for c in text_clean) and any(c.isalpha() for c in text_clean):
                return "license_plate"

        # House number: short numeric or alphanumeric
        if re.match(r'^[0-9]{1,5}[A-Z]?$', text_clean):
            return "house_number"

        # Street name patterns
        street_suffixes = ['ST', 'AVE', 'AVENUE', 'ROAD', 'RD', 'BLVD', 'DR', 'DRIVE', 'LN', 'LANE', 'WAY', 'CT', 'COURT']
        if any(text_clean.endswith(suffix) or f' {suffix}' in text_clean for suffix in street_suffixes):
            return "street_sign"

        return "other"

    def match_finding_to_text(
        self,
        finding: Dict[str, Any],
        text_regions: List[Dict[str, Any]],
        image_size: Tuple[int, int]
    ) -> Optional[Dict[str, int]]:
        """Match a Claude finding to a detected text region."""
        if not text_regions:
            return None

        region_hint = finding.get("region_hint", "").lower()
        category = finding.get("category", "")
        width, height = image_size

        # Get approximate region from hint
        bounds = self._get_region_bounds(region_hint)
        x_min = bounds[0] * width
        x_max = bounds[1] * width
        y_min = bounds[2] * height
        y_max = bounds[3] * height

        # Score each text region
        scored_regions = []
        for region in text_regions:
            bbox = region["bbox"]
            center_x = bbox["x"] + bbox["w"] / 2
            center_y = bbox["y"] + bbox["h"] / 2

            # Start with OCR confidence
            score = region["confidence"]

            # Check if in the hinted region (big bonus)
            in_region = x_min <= center_x <= x_max and y_min <= center_y <= y_max
            if in_region:
                score += 0.5

            # Match text type to category (big bonus)
            text_type = region.get("text_type", "other")
            if category == "license_plate" and text_type == "license_plate":
                score += 1.0
            elif category == "house_number" and text_type == "house_number":
                score += 1.0
            elif category == "street_sign" and text_type == "street_sign":
                score += 1.0

            # Only consider if somewhat relevant
            if in_region or (category == text_type):
                scored_regions.append((region, score))

        if not scored_regions:
            # Fall back: find any text that matches the category type
            for region in text_regions:
                text_type = region.get("text_type", "other")
                if category == text_type:
                    return region["bbox"]
            return None

        # Return the best match
        best_match = max(scored_regions, key=lambda x: x[1])
        return best_match[0]["bbox"]

    def _get_region_bounds(self, hint: str) -> Tuple[float, float, float, float]:
        """Parse region hint into bounds (x_min, x_max, y_min, y_max) as ratios."""
        x_min, x_max = 0, 1
        y_min, y_max = 0, 1

        if "left" in hint:
            x_max = 0.6
        if "right" in hint:
            x_min = 0.4
        if "top" in hint or "upper" in hint:
            y_max = 0.6
        if "bottom" in hint or "lower" in hint:
            y_min = 0.4
        if "center" in hint or "middle" in hint:
            x_min, x_max = 0.2, 0.8
            y_min, y_max = 0.2, 0.8

        return (x_min, x_max, y_min, y_max)

    def find_all_risky_text(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Find all potentially risky text (plates, numbers, signs)."""
        regions = self.detect_text_regions(image_bytes)

        risky = []
        for region in regions:
            text_type = region.get("text_type", "other")
            if text_type in ["license_plate", "house_number", "street_sign"]:
                risky.append(region)

        return risky


_detector: Optional[TextDetector] = None


def get_detector() -> TextDetector:
    """Get or create the text detector instance."""
    global _detector
    if _detector is None:
        _detector = TextDetector()
    return _detector
