from flask import Flask, request, jsonify
import whisper
import os
import tempfile

app = Flask(__name__)

# Global model - loaded once when server starts
_whisper_model = None

def get_whisper_model():
    """Load Whisper model once"""
    global _whisper_model
    if _whisper_model is None:
        model_path = "tiny.pt"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        print("Loading Whisper model...")
        _whisper_model = whisper.load_model(model_path, device="cpu")
        print("Model loaded on CPU!")
    return _whisper_model


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Transcribe audio file"""
    try:
        # Get audio file from request
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        audio_file = request.files['file']

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
            audio_file.save(f.name)
            temp_path = f.name

        # Transcribe
        print(f"Transcribing {audio_file.filename}...")
        model = get_whisper_model()
        result = model.transcribe(temp_path)
        transcription = result["text"].strip()

        # Cleanup
        os.unlink(temp_path)

        print(f"Result: {transcription}")

        return jsonify({
            "success": True,
            "transcription": transcription
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "running",
        "model_loaded": _whisper_model is not None
    })


if __name__ == '__main__':
    PORT = 8001

    print("=" * 50)
    print(f"Whisper Server Starting on Port {PORT}")
    print("=" * 50)
    print(f"POST http://localhost:{PORT}/transcribe")
    print(f"GET  http://localhost:{PORT}/health")
    print("=" * 50)

    app.run(host='0.0.0.0', port=PORT, debug=False)
