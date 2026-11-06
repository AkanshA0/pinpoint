"""Claude prompts for image analysis and verification."""

ANALYSIS_PROMPT = """Analyze this image for privacy risks. Focus on items that could identify a person or their location.

PRIORITY ITEMS TO DETECT (even if text is partially visible or at an angle):
1. ID cards, badges, or employee cards - even if worn on a lanyard, detect THE CARD ITSELF
2. License plates on vehicles
3. House/apartment numbers
4. Street name signs
5. Documents with personal information

DO NOT flag:
- Faces (never flag faces)
- Lanyard straps or lanyard brand text (only flag the ID CARD attached to it)
- Clothing, uniforms, or outfit colors
- Generic text on t-shirts
- Background people

For each risk found, respond with JSON:
{
  "findings": [
    {
      "id": 1,
      "category": "id_card | license_plate | house_number | street_sign | document | other",
      "description": "Brief description",
      "severity": "high | medium | low",
      "region_hint": "Precise location (e.g., 'hanging on chest', 'on the car at bottom left')",
      "has_text": true
    }
  ]
}

IMPORTANT:
- ID cards/badges are HIGH severity even if text is not fully readable - the photo and format can identify someone
- Be precise about location
- If nothing risky is found, return {"findings": []}
- Return ONLY valid JSON"""

VERIFICATION_PROMPT = """Check if any identifying information is still visible in this image:
- ID cards or badges (even partially visible)
- License plate numbers
- House/apartment numbers
- Street names
- Documents

DO NOT flag faces, clothing, or lanyard straps.

Respond with JSON:
{
  "findings": [
    {
      "id": 1,
      "category": "id_card | license_plate | house_number | street_sign | document | other",
      "description": "What is still visible",
      "severity": "high | medium | low",
      "region_hint": "Location in image",
      "has_text": true
    }
  ]
}

If nothing identifying is visible, return {"findings": []}.
Return ONLY valid JSON."""
