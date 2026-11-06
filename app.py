"""Flask app for Pinpoint privacy analysis."""

import os
import base64
from flask import Flask, render_template, request, jsonify
import anthropic

from analyzer import analyze_image_sync, verify_protection_sync
from protector import protect_image, create_annotated_image
from cloaker import cloak_with_face_focus
from risk import calculate_risk, get_risk_level

app = Flask(__name__)

# Initialize Anthropic client
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("Warning: ANTHROPIC_API_KEY not set")
client = anthropic.Anthropic(api_key=api_key)


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """Analyze an image for privacy risks."""
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"error": "No image provided"}), 400

        image_b64 = data["image"]

        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception:
            return jsonify({"error": "Invalid base64 image data"}), 400

        # Analyze with Claude
        analysis = analyze_image_sync(image_bytes, client)

        # Create annotated image
        if analysis["findings"]:
            annotated_bytes = create_annotated_image(image_bytes, analysis["findings"])
        else:
            annotated_bytes = image_bytes

        annotated_b64 = base64.b64encode(annotated_bytes).decode("utf-8")

        return jsonify({
            "findings": analysis["findings"],
            "risk_score": analysis["risk_score"],
            "risk_level": get_risk_level(analysis["risk_score"]),
            "annotated_image": annotated_b64
        })

    except Exception as e:
        print(f"Error in analyze: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/protect", methods=["POST"])
def protect():
    """Protect an image by blurring selected regions."""
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"error": "No image provided"}), 400

        image_b64 = data["image"]
        findings = data.get("findings", [])
        fix_ids = data.get("fix_ids", [])
        verify = data.get("verify", True)

        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception:
            return jsonify({"error": "Invalid base64 image data"}), 400

        # Calculate before score
        before_score = calculate_risk(findings)

        # Apply protection
        protected_bytes, applied_fixes = protect_image(image_bytes, findings, fix_ids)

        # Calculate remaining findings
        remaining_findings = [f for f in findings if f.get("id") not in fix_ids]
        after_score = calculate_risk(remaining_findings)

        # Verify if requested
        residual_risks = []
        if verify:
            verification = verify_protection_sync(protected_bytes, client)
            residual_risks = verification["residual_risks"]
            after_score = max(after_score, verification["risk_score"])

        protected_b64 = base64.b64encode(protected_bytes).decode("utf-8")

        return jsonify({
            "protected_image": protected_b64,
            "before_score": before_score,
            "after_score": after_score,
            "residual_risks": residual_risks
        })

    except Exception as e:
        print(f"Error in protect: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/cloak", methods=["POST"])
def cloak():
    """Apply privacy cloak to disrupt facial recognition."""
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"error": "No image provided"}), 400

        image_b64 = data["image"]
        intensity = data.get("intensity", 0.04)

        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception:
            return jsonify({"error": "Invalid base64 image data"}), 400

        # Apply cloaking
        cloaked_bytes, faces_found = cloak_with_face_focus(image_bytes, intensity)
        cloaked_b64 = base64.b64encode(cloaked_bytes).decode("utf-8")

        return jsonify({
            "cloaked_image": cloaked_b64,
            "faces_detected": faces_found,
            "message": "Cloaking applied with enhanced protection around detected faces" if faces_found else "Cloaking applied to entire image"
        })

    except Exception as e:
        print(f"Error in cloak: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
