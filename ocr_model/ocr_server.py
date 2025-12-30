from flask import Flask, request, jsonify
from doctr.models import ocr_predictor, detection, recognition
from doctr.io import DocumentFile
import os
import tempfile

app = Flask(__name__)

# Global models - loaded once when server starts
_ocr_predictor = None

def get_ocr_model():
    """Load OCR models once from local files"""
    global _ocr_predictor
    if _ocr_predictor is None:
        det_model_path = "db_mobilenet_v3_large.pt"
        reco_model_path = "crnn_mobilenet_v3_small.pt"

        # Check if model files exist
        if not os.path.exists(det_model_path):
            raise FileNotFoundError(f"Detection model not found: {det_model_path}")
        if not os.path.exists(reco_model_path):
            raise FileNotFoundError(f"Recognition model not found: {reco_model_path}")

        print("Loading OCR models...")

        # Load detection model (finds WHERE text is)
        det_model = detection.db_mobilenet_v3_large(pretrained=False)
        det_model.from_pretrained(det_model_path)
        print("✓ Detection model loaded (finds text regions)")

        # Load recognition model (reads WHAT text says)
        reco_model = recognition.crnn_mobilenet_v3_small(pretrained=False)
        reco_model.from_pretrained(reco_model_path)
        print("✓ Recognition model loaded (reads text)")

        # Create predictor with both models
        _ocr_predictor = ocr_predictor(
            det_arch=det_model,
            reco_arch=reco_model,
            pretrained=False
        )
        print("✓ OCR Predictor ready (100% offline)")

    return _ocr_predictor


@app.route('/ocr', methods=['POST'])
def perform_ocr():
    """Extract text from image"""
    try:
        # Get image file from request
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        image_file = request.files['file']

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            image_file.save(f.name)
            temp_path = f.name

        # Perform OCR
        print(f"Processing {image_file.filename}...")
        predictor = get_ocr_model()

        # Load document
        doc = DocumentFile.from_images([temp_path])

        # Run OCR (detection + recognition)
        result = predictor(doc)

        # Extract text from result
        text_output = []
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    line_text = " ".join([word.value for word in line.words])
                    confidence = sum([word.confidence for word in line.words]) / len(line.words) if line.words else 0
                    text_output.append({
                        "text": line_text,
                        "confidence": round(confidence, 3)
                    })

        # Combine all text
        full_text = "\n".join([item["text"] for item in text_output])

        # Cleanup
        os.unlink(temp_path)

        print(f"Extracted {len(text_output)} lines of text")

        return jsonify({
            "success": True,
            "text": full_text,
            "lines": text_output,
            "total_lines": len(text_output)
        })

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "running",
        "models_loaded": _ocr_predictor is not None,
        "detection_model": "db_mobilenet_v3_large (16MB)",
        "recognition_model": "crnn_mobilenet_v3_small (8MB)",
        "total_size": "24MB",
        "offline": True
    })


if __name__ == '__main__':
    PORT = 8002

    print("=" * 60)
    print(f"OCR Server Starting on Port {PORT}")
    print("=" * 60)
    print("Models:")
    print("  - Detection:    db_mobilenet_v3_large.pt (finds text regions)")
    print("  - Recognition:  crnn_mobilenet_v3_small.pt (reads text)")
    print("=" * 60)
    print(f"POST http://localhost:{PORT}/ocr")
    print(f"GET  http://localhost:{PORT}/health")
    print("=" * 60)

    app.run(host='0.0.0.0', port=PORT, debug=False)
