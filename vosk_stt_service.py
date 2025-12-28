import vosk
import wave
import json
import os

# Global model - loaded once and reused
_vosk_model = None

def get_vosk_model():
    """Get or create Vosk model (lazy loading)"""
    global _vosk_model
    if _vosk_model is None:
        model_path = "vosk-model-small-en-us-0.15"
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Vosk model not found at '{model_path}'. "
                "Please download from https://alphacephei.com/vosk/models"
            )
        _vosk_model = vosk.Model(model_path)
    return _vosk_model


def transcribe_audio_vosk(audio_file_path):
    """
    Transcribe audio file using Vosk

    Args:
        audio_file_path: Path to WAV audio file

    Returns:
        str: Transcribed text

    Raises:
        Exception: If transcription fails
    """
    try:
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Open WAV file
        wf = wave.open(audio_file_path, "rb")

        # Validate audio format
        if wf.getnchannels() != 1:
            raise ValueError("Audio must be mono (1 channel)")
        if wf.getsampwidth() != 2:
            raise ValueError("Audio must be 16-bit")
        if wf.getframerate() not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Unsupported sample rate: {wf.getframerate()}")

        # Create recognizer with actual sample rate
        model = get_vosk_model()
        recognizer = vosk.KaldiRecognizer(model, wf.getframerate())

        # Process audio in chunks
        transcription = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if result.get("text"):
                    transcription += result["text"] + " "

        # Get final result
        final_result = json.loads(recognizer.FinalResult())
        if final_result.get("text"):
            transcription += final_result["text"]

        wf.close()

        return transcription.strip()

    except Exception as e:
        raise Exception(f"Vosk transcription failed: {str(e)}")


def transcribe_audio_vosk_realtime():
    """
    Real-time transcription from microphone (original functionality)
    This is the live microphone version for reference
    """
    import pyaudio

    model = get_vosk_model()
    recognizer = vosk.KaldiRecognizer(model, 16000)

    mic = pyaudio.PyAudio()
    stream = mic.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8192
    )
    stream.start_stream()

    print("Listening... (Ctrl+C to stop)")

    try:
        while True:
            data = stream.read(4096, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                print(f"You said: {result['text']}")
            else:
                partial = json.loads(recognizer.PartialResult())
                print(f"Partial: {partial['partial']}", end='\r')
    except KeyboardInterrupt:
        print("\nStopped listening")
    finally:
        stream.stop_stream()
        stream.close()
        mic.terminate()


# Test function (only runs when script is executed directly)
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Test with audio file
        test_audio = sys.argv[1]
        print(f"Transcribing: {test_audio}")
        transcription = transcribe_audio_vosk(test_audio)
        print(f"Transcription: {transcription}")
    else:
        # Run real-time mode
        print("Starting real-time mode...")
        transcribe_audio_vosk_realtime()