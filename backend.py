
import os
import re
import json
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

import google.generativeai as genai

# ── Load .env ─────────────────────────────
load_dotenv(dotenv_path=".env")

API_KEY = os.getenv("GEMINI_API_KEY")
print("✅ API KEY:", API_KEY)

# ── Gemini Setup ─────────────────────────
if not API_KEY:
    print("❌ ERROR: API key not found. Check .env file")

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

app = Flask(__name__)
CORS(app)

# ── PDF / DOCX Support ───────────────────
try:
    import fitz
    PDF_SUPPORT = True
except:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except:
    DOCX_SUPPORT = False


# ── FALLBACK ─────────────────────────────
def fallback_response(user_input):
    return "⚠️ AI not working. Showing fallback response.\n\nTry fixing API key."


# ── AI CALL ─────────────────────────────
def call_ai(prompt):
    try:
        response = model.generate_content(prompt)

        if response and hasattr(response, "text"):
            return response.text

        return "⚠️ No response from AI"

    except Exception as e:
        print("❌ Gemini ERROR:", e)
        return fallback_response(prompt)


# ── CHAT API ─────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        messages = data.get("messages", [])

        user_input = messages[-1]["content"]
        prompt = f"""
        You are an AI Career Mentor.

        Give a structured answer with:
        - roadmap
        - skills
        - projects
        - tips

        User question:
        {user_input}
        """

        reply = call_ai(prompt)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── FILE TEXT EXTRACT ───────────────────
def extract_text(file):
    filename = file.filename.lower()

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        file.save(tmp.name)
        path = tmp.name

    text = ""

    try:
        if filename.endswith(".pdf") and PDF_SUPPORT:
            import fitz
            doc = fitz.open(path)
            text = "\n".join([p.get_text() for p in doc])
            doc.close()

        elif filename.endswith(".docx") and DOCX_SUPPORT:
            from docx import Document
            doc = Document(path)
            text = "\n".join([p.text for p in doc.paragraphs])

    except Exception as e:
        print("File error:", e)

    finally:
        try:
            os.remove(path)
        except:
            pass

    return text


# ── CV ANALYSIS ─────────────────────────
@app.route("/analyze-cv", methods=["POST"])
def analyze_cv():
    try:
        file = request.files["file"]
        text = extract_text(file).lower()

        skills = []
        if "python" in text:
            skills.append("Python")
        if "sql" in text:
            skills.append("SQL")
        if "machine learning" in text:
            skills.append("Machine Learning")

        missing = []
        if "python" not in text:
            missing.append("Python")
        if "projects" not in text:
            missing.append("Projects")
        if "github" not in text:
            missing.append("GitHub")

        analysis = {
            "overall_score": 70,
            "detected_skills": skills,
            "missing_skills": missing,
            "strengths": [
                "Good resume structure",
                "Clear sections"
            ],
            "improvements": [
                {
                    "issue": "No projects mentioned",
                    "fix": "Add 2–3 real-world projects"
                },
                {
                    "issue": "No GitHub link",
                    "fix": "Include GitHub profile"
                }
            ],
            "suggestions": [
                "Add measurable achievements",
                "Use action verbs (Built, Developed, Designed)",
                "Customize resume for job roles"
            ]
        }

        return jsonify({"analysis": analysis})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── HEALTH ─────────────────────────────
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "api_key_loaded": bool(API_KEY),
        "pdf_support": PDF_SUPPORT,
        "docx_support": DOCX_SUPPORT
    })


# ── RUN ─────────────────────────────
if __name__ == "__main__":
    print("🚀 Backend running at http://localhost:5000")
    app.run(debug=True)
