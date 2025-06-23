"""
Herramienta de Análisis y Síntesis Avanzada de Texto (analyze_text_for_insights)
Procesa texto para identificar temas clave, entidades, sentimiento y generar un resumen ejecutivo.
"""
import spacy
from keybert import KeyBERT
from transformers import pipeline
from textblob import TextBlob

_nlp = None
_kw_model = None
_summarizer = None

def get_spacy_model():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def get_keybert_model():
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT("all-MiniLM-L6-v2")
    return _kw_model

def get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    return _summarizer

def analyze_text_for_insights(text, summary_max_length=130):
    """
    Procesa el texto y retorna un dict con temas clave, entidades, sentimiento y resumen.
    """
    kw_model = get_keybert_model()
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 3), stop_words="english", top_n=8)
    temas_clave = [kw[0] for kw in keywords]

    nlp = get_spacy_model()
    doc = nlp(text)
    entidades = []
    for ent in doc.ents:
        entidades.append({
            "texto": ent.text,
            "tipo": ent.label_
        })

    blob = TextBlob(text)
    sentimiento = {
        "polarity": blob.sentiment.polarity,
        "subjectivity": blob.sentiment.subjectivity
    }

    summarizer = get_summarizer()
    resumen = ""
    if len(text) > 500:
        resumen = summarizer(text, max_length=summary_max_length, min_length=40, do_sample=False)[0]['summary_text']
    else:
        resumen = text if len(text) < summary_max_length else text[:summary_max_length] + "..."

    return {
        "temas_clave": temas_clave,
        "entidades": entidades,
        "sentimiento": sentimiento,
        "resumen_ejecutivo": resumen
    }
