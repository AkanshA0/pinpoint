"""Image cloaking to disrupt facial recognition."""

import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple


def cloak_image(image_bytes: bytes, intensity: float = 0.03) -> bytes:
    """
    Apply privacy-preserving perturbations to an image.

    This adds subtle noise patterns that can disrupt facial recognition
    systems while keeping the image visually similar to the original.

    Args:
        image_bytes: Original image as bytes
        intensity: Noise intensity (0.01-0.1, default 0.03)

    Returns:
        Cloaked image as bytes
    """
    # Load image
    pil_image = Image.open(io.BytesIO(image_bytes))

    if pil_image.mode in ('RGBA', 'P'):
        pil_image = pil_image.convert('RGB')

    img_array = np.array(pil_image, dtype=np.float32) / 255.0

    # Generate structured noise (more effective than random noise)
    h, w, c = img_array.shape

    # 1. High-frequency pattern noise (disrupts feature extraction)
    freq_noise = np.zeros_like(img_array)
    for i in range(c):
        # Create checkerboard-like pattern at different scales
        x = np.arange(w)
        y = np.arange(h)
        xx, yy = np.meshgrid(x, y)
        pattern = np.sin(xx * 0.5) * np.sin(yy * 0.5) * 0.5
        pattern += np.sin(xx * 0.25) * np.sin(yy * 0.25) * 0.3
        pattern += np.sin(xx * 0.125) * np.sin(yy * 0.125) * 0.2
        freq_noise[:, :, i] = pattern

    # 2. Gaussian noise for randomness
    gaussian_noise = np.random.randn(h, w, c) * 0.5

    # Combine noise types
    combined_noise = freq_noise * 0.6 + gaussian_noise * 0.4

    # Normalize and scale
    combined_noise = combined_noise / np.abs(combined_noise).max()
    combined_noise *= intensity

    # Apply noise
    cloaked = img_array + combined_noise
    cloaked = np.clip(cloaked, 0, 1)

    # Convert back to uint8
    cloaked_uint8 = (cloaked * 255).astype(np.uint8)

    # Apply subtle color shift (further disrupts recognition)
    cloaked_uint8 = apply_color_shift(cloaked_uint8)

    # Convert to PIL and bytes
    result_image = Image.fromarray(cloaked_uint8)

    # Strip metadata
    buffer = io.BytesIO()
    result_image.save(buffer, format='JPEG', quality=95)

    return buffer.getvalue()


def apply_color_shift(img: np.ndarray, shift: int = 2) -> np.ndarray:
    """Apply subtle color channel shifts."""
    result = img.copy()

    # Slight shift in color channels
    result[:, :, 0] = np.clip(result[:, :, 0].astype(np.int16) + shift, 0, 255).astype(np.uint8)
    result[:, :, 2] = np.clip(result[:, :, 2].astype(np.int16) - shift, 0, 255).astype(np.uint8)

    return result


def cloak_with_face_focus(image_bytes: bytes, intensity: float = 0.04) -> Tuple[bytes, bool]:
    """
    Apply stronger cloaking around detected faces.

    Returns:
        Tuple of (cloaked image bytes, whether faces were detected)
    """
    pil_image = Image.open(io.BytesIO(image_bytes))

    if pil_image.mode in ('RGBA', 'P'):
        pil_image = pil_image.convert('RGB')

    img_array = np.array(pil_image)
    cv_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # Try to detect faces
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    faces_found = len(faces) > 0

    # Create intensity mask (higher around faces)
    h, w = img_array.shape[:2]
    intensity_mask = np.ones((h, w), dtype=np.float32) * intensity

    if faces_found:
        for (x, y, fw, fh) in faces:
            # Expand face region slightly
            x1 = max(0, x - fw // 4)
            y1 = max(0, y - fh // 4)
            x2 = min(w, x + fw + fw // 4)
            y2 = min(h, y + fh + fh // 4)

            # Higher intensity around faces
            intensity_mask[y1:y2, x1:x2] = intensity * 1.5

    # Apply cloaking with variable intensity
    img_float = img_array.astype(np.float32) / 255.0

    # Generate noise
    noise = np.random.randn(h, w, 3) * 0.5
    freq = np.zeros((h, w, 3), dtype=np.float32)
    x = np.arange(w)
    y = np.arange(h)
    xx, yy = np.meshgrid(x, y)
    for i in range(3):
        freq[:, :, i] = np.sin(xx * 0.4 + i) * np.sin(yy * 0.4 + i)

    combined = (noise * 0.4 + freq * 0.6)
    combined = combined / np.abs(combined).max()

    # Apply with mask
    for i in range(3):
        img_float[:, :, i] += combined[:, :, i] * intensity_mask

    img_float = np.clip(img_float, 0, 1)
    result = (img_float * 255).astype(np.uint8)
    result = apply_color_shift(result)

    # Convert to bytes
    result_image = Image.fromarray(result)
    buffer = io.BytesIO()
    result_image.save(buffer, format='JPEG', quality=95)

    return buffer.getvalue(), faces_found
