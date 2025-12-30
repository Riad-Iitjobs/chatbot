import whisper
import os

# Global model - loaded once and reused
_whisper_model = None

def get_whisper_model():
    """Get or create Whisper model (lazy loading)"""
    global _whisper_model
    if _whisper_model is None:
        model_path = "tiny.pt"
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Whisper model not found at '{model_path}'. "
                "Please download from https://github.com/openai/whisper"
            )
        _whisper_model = whisper.load_model(model_path, device="cpu")
    return _whisper_model


def transcribe_audio_whisper(audio_file_path):
    """
    Transcribe audio file using Whisper

    Args:
        audio_file_path: Path to audio file (mp3, wav, m4a, etc.)

    Returns:
        str: Transcribed text

    Raises:
        Exception: If transcription fails
    """
    try:
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        model = get_whisper_model()
        result = model.transcribe(audio_file_path)

        return result["text"].strip()

    except Exception as e:
        raise Exception(f"Whisper transcription failed: {str(e)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Test with audio file
        test_audio = sys.argv[1]
        print(f"Transcribing: {test_audio}")
        transcription = transcribe_audio_whisper(test_audio)
        print(f"Transcription: {transcription}")
    else:
        print("Usage: python stt_whisper_service.py <audio_file_path>")