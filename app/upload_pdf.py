import requests
import os

url = "http://127.0.0.1:8000/api/upload"
file_path = r"C:/Desktop/ai-pdf-chatbot/app/data/raw/Base-Paper-TS.pdf"

# Extract just the filename
filename = os.path.basename(file_path)

with open(file_path, "rb") as f:
    files = {"file": (filename, f, "application/pdf")}
    response = requests.post(url, files=files)

print(response.json())
