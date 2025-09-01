import json
import os
import re
import tempfile
import pdfplumber
import docx
import pytesseract
from PIL import Image
import requests
from flask import jsonify

# Gemini API setup
GEMINI_API_KEY = "AIzaSyAmZJdcxZHtPKDJ-dGhNnGARNBIrXYeyQc"  # Replace with your Gemini API Key
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# --------------------------------------------------------
# Function: Build DropOut Catcher Prompt
# --------------------------------------------------------
def build_dropout_prompt(extracted_text):
    prompt_text = (
        "You are 'DropOut Catcher', an advanced Educational AI system designed to prevent student dropouts.\n\n"
        "🎯 Key Features:\n"
        "- Dropout prediction\n"
        "- Learning analytics\n"
        "- Early intervention\n"
        "- Performance tracking\n\n"
        "📌 Use Cases:\n"
        "- Student retention\n"
        "- Academic support\n"
        "- Performance monitoring\n"
        "- Curriculum optimization\n\n"
        "Instructions:\n"
        "Analyze the student academic data, attendance, and behavioral notes carefully.\n"
        "Return your prediction in *strict JSON format only*.\n\n"
        "The output must strictly follow this JSON structure:\n"
        "{\n"
        '  "at_risk_students": ["List of student names who are at risk"],\n'
        '  "risk_factors": ["List of reasons (low attendance, poor grades, low engagement, etc.)"],\n'
        '  "intervention_strategies": ["List of actionable steps for teachers/parents/admin"],\n'
        '  "success_probability": 0.xx\n'
        "}\n\n"
        f"Student Input:\n{extracted_text}"
    )
    return {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt_text}]
            }
        ]
    }

# --------------------------------------------------------
# Function: Query Gemini API
# --------------------------------------------------------
def query_gemini(prompt):
    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    payload = build_dropout_prompt(prompt)
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]

# --------------------------------------------------------
# Functions: Extract Text from Files
# --------------------------------------------------------
def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs]).strip()

def extract_text_from_image(file_path):
    image = Image.open(file_path)
    return pytesseract.image_to_string(image).strip()

# --------------------------------------------------------
# Main Cloud Function
# --------------------------------------------------------
def dropout_catcher(request):
    try:
        extracted_text = ""

        # ---------- 1. Handle File Upload ----------
        if request.files:
            file = next(iter(request.files.values()))
            suffix = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                temp_path = tmp.name
            try:
                if suffix == ".pdf":
                    extracted_text = extract_text_from_pdf(temp_path)
                elif suffix == ".docx":
                    extracted_text = extract_text_from_docx(temp_path)
                elif suffix in [".png", ".jpg", ".jpeg"]:
                    extracted_text = extract_text_from_image(temp_path)
                elif suffix in [".txt", ".log"]:
                    with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                        extracted_text = f.read()
                else:
                    return jsonify({"error": "Unsupported file format"}), 400
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # ---------- 2. Handle JSON Input ----------
        if not extracted_text and request.is_json:
            data = request.get_json(silent=True)
            if data and "text" in data:
                extracted_text = data["text"]

        # ---------- 3. Handle Plain Text ----------
        if not extracted_text:
            raw_text = request.data.decode("utf-8").strip()
            if raw_text:
                extracted_text = raw_text

        # ---------- 4. Validate Input ----------
        if not extracted_text:
            return jsonify({"error": "No input provided"}), 400

        # Limit to first 10,000 characters
        extracted_text = extracted_text[:10000]

        # ---------- 5. Call Gemini API ----------
        ai_response = query_gemini(extracted_text)
        clean_response = re.sub(r"json|```", "", ai_response).strip()
        json_result = json.loads(clean_response)

        return jsonify(json_result), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON received from API"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------------------------------------------
# Flask App for Local Testing
# --------------------------------------------------------

from flask import Flask, request, jsonify
app = Flask(__name__)
# Default homepage route
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "DropOut Catcher API is running ✅",
        "routes": ["/dropout (GET, POST)"]
    }), 200
# 🎯 Main route for analyzing student data
@app.route("/", methods=["POST"])
def analyze():
    return dropout_catcher(request)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

# POST route for analysis





