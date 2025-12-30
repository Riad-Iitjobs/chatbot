"""Test script for OCR server"""
import requests

# Test health endpoint
print("Testing health endpoint...")
response = requests.get("http://localhost:8002/health")
print(response.json())

# Test OCR endpoint (example)
# Uncomment and modify with your image path:
# with open('your_image.jpg', 'rb') as f:
#     files = {'file': f}
#     response = requests.post("http://localhost:8002/ocr", files=files)
#     print(response.json())
