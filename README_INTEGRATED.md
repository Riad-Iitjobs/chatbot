# Integrated Chatbot with OCR & Whisper

Complete chatbot system with Gemini AI, OCR, and Speech-to-Text capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER'S BROWSER                        │
│              http://localhost:8501                       │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────┐
│         STREAMLIT APP (Port 8501)                       │
│         app_integrated.py                                │
│                                                          │
│  Orchestrates:                                           │
│  • User interface                                        │
│  • Gemini API calls                                      │
│  • DuckDB queries                                        │
│  • File processing                                       │
│  • Server coordination                                   │
│                                                          │
│  Forwards requests to:                                   │
│    ├─ Whisper Server (audio)                            │
│    └─ OCR Server (images)                               │
└────┬────────────────────────┬────────────────────────────┘
     │                        │
     ↓                        ↓
┌──────────────────┐    ┌──────────────────┐
│ Whisper Server   │    │ OCR Server       │
│ Port 8001        │    │ Port 8002        │
│                  │    │                  │
│ • Loads tiny.pt  │    │ • Detection      │
│ • Transcribes    │    │ • Recognition    │
│   audio          │    │ • Returns text   │
└──────────────────┘    └──────────────────┘
```

---

## Installation

### 1. Install Python packages:
```bash
pip install streamlit python-doctr[torch] openai-whisper flask requests python-dotenv google-generativeai pypdf pillow duckdb
```

### 2. Set up environment:
```bash
# Create .env file
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

### 3. Verify models are downloaded:
```bash
ls whisper_model/tiny.pt          # Should be ~72MB
ls ocr_model/db_mobilenet_v3_large.pt     # Should be ~16MB
ls ocr_model/crnn_mobilenet_v3_small.pt   # Should be ~8MB
```

---

## Quick Start

### Option 1: Start All Services at Once (Recommended)
```bash
./start_all.sh
```

This launches all 3 servers in the background. Open your browser to:
**http://localhost:8501**

To stop everything:
```bash
./stop_all.sh
```

### Option 2: Start Manually (3 terminals)

**Terminal 1 - Whisper Server:**
```bash
cd whisper_model
python whisper_server.py
# Running on http://localhost:8001
```

**Terminal 2 - OCR Server:**
```bash
cd ocr_model
python ocr_server.py
# Running on http://localhost:8002
```

**Terminal 3 - Streamlit App:**
```bash
streamlit run app_integrated.py
# Running on http://localhost:8501
```

---

## Features & Usage

### 1. **Text Chat**
Just type and chat with Gemini AI.

### 2. **PDF Upload**
- Upload PDF files
- Text is automatically extracted
- Ask questions about the PDF content

### 3. **CSV Upload**
- Upload CSV files
- Automatic schema detection with DuckDB
- Ask natural language questions → Get SQL query results

### 4. **Image Upload (Two Modes)**

#### **OCR Mode** (Extract Text):
- Select "📄 OCR" option
- Sends image to OCR server (port 8002)
- Extracts text using Detection + Recognition models
- Returns text with confidence scores
- Good for: invoices, receipts, documents, screenshots

#### **Vision Mode** (AI Understanding):
- Select "🔷 Gemini Vision" option
- Sends image directly to Gemini API
- AI can understand, describe, analyze the image
- Good for: charts, diagrams, photos, complex images

### 5. **Audio File Upload** (New!)
- Upload MP3 or WAV files
- Automatically sent to Whisper server (port 8001)
- Transcription added to chat context
- Ask questions about the transcribed content

### 6. **Voice Input (Microphone)**
- Click 🎤 Voice button
- Record audio directly in browser
- Sent to Whisper server for transcription
- Transcribed text appears in chat input

---

## File Type Handling

| File Type | Processing | Server Used | Result |
|-----------|-----------|-------------|--------|
| `.pdf` | Text extraction | None (pypdf) | Text context for Gemini |
| `.csv` | Schema detection | None (DuckDB) | SQL query capability |
| `.png`, `.jpg`, `.webp` | OCR or Vision | OCR (8002) or Gemini | Text or AI understanding |
| `.mp3`, `.wav` | Speech-to-text | Whisper (8001) | Transcribed text |
| 🎤 Recording | Speech-to-text | Whisper (8001) | Transcribed text |

---

## Server Status Indicators

The sidebar shows real-time server status:
- 🟢 Green = Server running and healthy
- 🔴 Red = Server offline

If a server is offline:
- **Whisper offline**: Voice features disabled
- **OCR offline**: Only Vision mode available for images

---

## Request Flow Examples

### **Example 1: OCR an Invoice**
```
1. User uploads invoice.png
2. User selects "OCR" mode
3. Streamlit saves temp file
4. Streamlit → POST http://localhost:8002/ocr (sends image)
5. OCR Server:
   - Detection model finds text regions
   - Recognition model reads text
   - Returns: {"text": "Invoice #12345...", "confidence": 0.95}
6. Streamlit receives OCR result
7. User asks: "What's the invoice number?"
8. Gemini receives question + OCR text
9. Gemini responds: "The invoice number is 12345"
```

### **Example 2: Transcribe Audio File**
```
1. User uploads recording.mp3
2. Streamlit detects audio file type
3. Streamlit → POST http://localhost:8001/transcribe (sends audio)
4. Whisper Server:
   - Loads tiny.pt model
   - Transcribes audio
   - Returns: {"transcription": "Hello, this is a test"}
5. Streamlit receives transcription
6. User can now ask questions about the transcribed content
```

### **Example 3: Voice Input**
```
1. User clicks 🎤 Voice button
2. User records audio in browser
3. Browser sends audio to Streamlit
4. Streamlit → POST http://localhost:8001/transcribe
5. Whisper Server transcribes
6. Transcription appears in chat input
7. User can edit or send directly
```

---

## Configuration

Edit at the top of `app_integrated.py`:

```python
WHISPER_SERVER_URL = "http://localhost:8001"
OCR_SERVER_URL = "http://localhost:8002"
```

Change ports if needed.

---

## Troubleshooting

### Servers won't start:
```bash
# Check if ports are already in use
lsof -i:8001  # Whisper
lsof -i:8002  # OCR
lsof -i:8501  # Streamlit

# Kill processes on ports
lsof -ti:8001 | xargs kill -9
```

### Server status shows offline:
```bash
# Test Whisper server
curl http://localhost:8001/health

# Test OCR server
curl http://localhost:8002/health

# Check logs
tail -f logs/whisper.log
tail -f logs/ocr.log
tail -f logs/streamlit.log
```

### Import errors:
```bash
# Make sure all packages installed
pip install -r requirements.txt  # (if you create one)

# Verify in venv
which python
```

### Model not found:
```bash
# Verify models exist
ls -lh whisper_model/tiny.pt
ls -lh ocr_model/*.pt
```

---

## Performance Notes

### First Request After Starting:
- Whisper: ~2-5 seconds (loading model)
- OCR: ~3-7 seconds (loading 2 models)

### Subsequent Requests:
- Whisper: <1 second (small audio)
- OCR: 1-3 seconds (depending on image size)

### Model Sizes:
- Whisper: 72 MB (tiny.pt)
- OCR Detection: 16 MB (db_mobilenet_v3_large.pt)
- OCR Recognition: 8 MB (crnn_mobilenet_v3_small.pt)
- **Total: 96 MB** (all models combined)

---

## Logs

All logs are saved to `logs/` directory:
- `logs/whisper.log` - Whisper server logs
- `logs/ocr.log` - OCR server logs
- `logs/streamlit.log` - Streamlit app logs

View live:
```bash
tail -f logs/*.log
```

---

## Differences from Original App

### Old (`app.py`):
- Voice input imported STT functions directly
- Images only sent to Gemini Vision
- No audio file upload support
- No OCR capability

### New (`app_integrated.py`):
- ✅ Voice input via Whisper server (HTTP)
- ✅ Images: Choose OCR or Vision mode
- ✅ Audio file upload support (MP3/WAV)
- ✅ OCR server integration
- ✅ Server health monitoring
- ✅ Unified architecture

---

## API Endpoints

### Whisper Server (8001):
- `POST /transcribe` - Transcribe audio file
- `GET /health` - Server health check

### OCR Server (8002):
- `POST /ocr` - Extract text from image
- `GET /health` - Server health check

### Example Usage:
```bash
# Test Whisper
curl -X POST -F "file=@audio.mp3" http://localhost:8001/transcribe

# Test OCR
curl -X POST -F "file=@invoice.png" http://localhost:8002/ocr
```

---

## Next Steps

1. Start all services: `./start_all.sh`
2. Open browser: http://localhost:8501
3. Try uploading different file types!
4. Experiment with OCR vs Vision mode for images

Enjoy your integrated chatbot! 🚀
