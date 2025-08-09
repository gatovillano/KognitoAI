import logging
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger(__name__)

class Reranker:
    _instance = None
    _model = None
    _tokenizer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Reranker, cls).__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        try:
            logger.info(f"Cargando modelo de reranking: {model_name}...")
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self._model.eval() # Poner el modelo en modo evaluación
            logger.info("✅ Modelo de reranking cargado exitosamente.")
        except Exception as e:
            logger.error(f"❌ Error al cargar el modelo de reranking {model_name}: {e}", exc_info=True)
            self._model = None
            self._tokenizer = None

    async def rerank(self, query: str, documents: list[str]) -> list[tuple[str, float]]:
        if not self._model or not self._tokenizer:
            logger.warning("Modelo de reranking no cargado. Saltando reranking.")
            return [(doc, 0.0) for doc in documents] # Devolver documentos sin rerankear

        if not documents:
            return []

        features = self._tokenizer([query] * len(documents), documents, padding=True, truncation=True, return_tensors='pt')

        with torch.no_grad():
            scores = self._model(**features).logits.squeeze().tolist()

        if not isinstance(scores, list):
            scores = [scores] # Asegurar que scores sea una lista si solo hay un documento

        reranked_documents = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        logger.info(f"Documentos rerankeados. Top 3 scores: {[round(s, 4) for _, s in reranked_documents[:3]]}")
        return reranked_documents

# Instanciar el reranker como un singleton
reranker = Reranker()
