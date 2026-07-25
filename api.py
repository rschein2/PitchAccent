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
        "accent_variants": result.accent_variants,
        "mora_count": result.mora_count,
        "pattern": result.pattern,
        "contour": result.contour,
        "source": result.source,
        "corrections": result.corrections,
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
                "accent_variants": w.accent_variants,
                "lemma": w.lemma,
                "source": w.source,
            }
            for w in parsed.words
        ],
    }


class CompoundRequest(BaseModel):
    phrase: str


@app.post("/compound")
def compound(req: CompoundRequest):
    """Break down a phrase into components and show accent for each level.
    E.g., 重い感染症 → [重い, 感染, 感染症, 重い感染症] each with accent."""
    engine = get_engine()
    parser = get_parser()

    # Parse the full phrase
    parsed = parser.parse_sentence(req.phrase)

    # Collect individual words + the full phrase
    results = []
    seen = set()

    for w in parsed.words:
        if w.surface not in seen and w.pos1 in ('名詞', '動詞', '形容詞', '副詞', '形状詞'):
            try:
                r = engine.analyze(w.surface)
                results.append({
                    "surface": w.surface,
                    "reading": r.reading if r else w.reading,
                    "accent_type": r.accent_type if r else 0,
                    "accent_variants": r.accent_variants if r else [],
                    "pattern": r.pattern if r else "",
                    "contour": r.contour if r else "",
                    "lemma": w.lemma,
                    "source": r.source if r else "unidic",
                })
                seen.add(w.surface)
            except:
                pass

    # Also analyze subcompounds if phrase has multiple morphemes
    # Build progressively longer compounds from the right
    if len(parsed.words) > 1:
        content_words = [w for w in parsed.words if w.pos1 in ('名詞', '動詞', '形容詞', '副詞', '形状詞')]
        for i in range(len(content_words) - 1):
            compound_surface = ''.join(w.surface for w in content_words[i:])
            if compound_surface not in seen:
                try:
                    r = engine.analyze(compound_surface)
                    results.append({
                        "surface": compound_surface,
                        "reading": r.reading if r else "",
                        "accent_type": r.accent_type if r else 0,
                        "pattern": r.pattern if r else "",
                        "contour": r.contour if r else "",
                        "lemma": compound_surface,
                        "is_compound": True,
                        "source": r.source if r else "unidic",
                    })
                    seen.add(compound_surface)
                except:
                    pass

    # Full phrase if not already covered
    full = req.phrase.strip()
    if full not in seen:
        try:
            r = engine.analyze(full)
            results.append({
                "surface": full,
                "reading": r.reading if r else "",
                "accent_type": r.accent_type if r else 0,
                "pattern": r.pattern if r else "",
                "contour": r.contour if r else "",
                "lemma": full,
                "is_compound": True,
                "source": r.source if r else "unidic",
            })
        except:
            pass

    return {"phrase": req.phrase, "components": results}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
