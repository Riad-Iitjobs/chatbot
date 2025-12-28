from transformers import pipeline
import os

# Global pipeline - loaded once and reused
_whisper_pipe = None

def get_whisper_pipeline():
    """Get or create Whisper pipeline (lazy loading)"""
    global _whisper_pipe
    if _whisper_pipe is None:
        _whisper_pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-tiny"
        )
    return _whisper_pipe


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

        pipe = get_whisper_pipeline()
        result = pipe(audio_file_path)

        return result["text"].strip()

    except Exception as e:
        raise Exception(f"Whisper transcription failed: {str(e)}")


# Test function (only runs when script is executed directly)
if __name__ == "__main__":
    test_audio = "audio.mp3"
    if os.path.exists(test_audio):
        transcription = transcribe_audio_whisper(test_audio)
        print(f"Transcription: {transcription}")
    else:
        print(f"Test audio file '{test_audio}' not found")