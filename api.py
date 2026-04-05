"""
FastAPI wrapper for the pitch accent engine.
Endpoints:
  POST /analyze  — analyze a word: accent, reading, forms
  POST /forms    — get all conjugated forms for a word
  POST /parse    — morphological parse of a sentence
  GET  /health   — health check
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Pitch Accent API", version="0.1.0")

# CORS — allow calls from any origin (Next.js app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-load heavy components
_engine = None
_parser = None
_conjugator = None


def get_engine():
    global _engine
    if _engine is None:
        from pitch_accent import FugashiAccentEngine
        _engine = FugashiAccentEngine()
    return _engine


def get_parser():
    global _parser
    if _parser is None:
        from pitch_accent import SentenceParser
        _parser = SentenceParser()
    return _parser


def get_conjugator():
    global _conjugator
    if _conjugator is None:
        from pitch_accent import VerbConjugator
        _conjugator = VerbConjugator()
    return _conjugator


# --- Request/Response models ---

class AnalyzeRequest(BaseModel):
    word: str
    context: Optional[str] = None


class FormsRequest(BaseModel):
    word: str


class ParseRequest(BaseModel):
    text: str


# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    engine = get_engine()
    result = engine.analyze(req.word)
    if result is None:
        return {"error": "Could not analyze word", "word": req.word}

    return {
        "surface": result.surface,
        "reading": result.reading,
        "accent_type": result.accent_type,
        "mora_count": result.mora_count,
        "pattern": result.pattern,
        "contour": result.contour,
    }


@app.post("/forms")
def forms(req: FormsRequest):
    """Get all conjugated forms of a verb/adjective."""
    conjugator = get_conjugator()
    try:
        results = conjugator.get_all_conjugations(req.word)
        if results is None:
            return {"word": req.word, "forms": [], "error": "Could not conjugate (not a verb/adjective?)"}
        return {
            "word": req.word,
            "forms": [
                {
                    "form_name": r.form_name,
                    "surface": r.surface,
                    "reading": r.reading,
                    "accent_type": r.accent_type,
                    "pattern": r.pattern,
                }
                for r in results
            ],
        }
    except Exception as e:
        return {"error": str(e), "word": req.word, "forms": []}


@app.post("/parse")
def parse(req: ParseRequest):
    """Morphological parse of a sentence — returns each word with reading and accent."""
    parser = get_parser()
    parsed = parser.parse_sentence(req.text)
    return {
        "text": req.text,
        "words": [
            {
                "surface": w.surface,
                "reading": w.reading,
                "pos": w.pos1,
                "accent_type": w.aType,
                "lemma": w.lemma,
            }
            for w in parsed.words
        ],
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
