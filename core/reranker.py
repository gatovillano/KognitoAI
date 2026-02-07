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

    async def rerank(self, query: str, documents: list, top_n: int = None, threshold: float = None) -> list:
        if not self._model or not self._tokenizer:
            logger.warning("Modelo de reranking no cargado. Saltando reranking.")
            return documents

        if not documents:
            return []

        # Usar valores de settings si no se proporcionan explícitamente
        from core.config import settings
        final_top_n = top_n if top_n is not None else settings.reranker_top_n
        final_threshold = threshold if threshold is not None else settings.reranker_threshold

        document_contents = [doc.page_content for doc in documents]
        features = self._tokenizer([query] * len(document_contents), document_contents, padding=True, truncation=True, return_tensors='pt')

        with torch.no_grad():
            scores = self._model(**features).logits.squeeze().tolist()

        if not isinstance(scores, list):
            scores = [scores]

        for doc, score in zip(documents, scores):
            doc.metadata['rerank_score'] = score

        # 1. Ordenar por score
        reranked_documents = sorted(documents, key=lambda x: x.metadata['rerank_score'], reverse=True)
        
        # 2. Filtrar por umbral de relevancia (Thresholding)
        filtered_documents = [doc for doc in reranked_documents if doc.metadata['rerank_score'] >= final_threshold]
        
        # 3. Limitar a Top N
        final_documents = filtered_documents[:final_top_n]
        
        logger.info(f"✨ Reranking: Recibidos {len(documents)}, filtrados {len(filtered_documents)}, devueltos {len(final_documents)} (Umbral: {final_threshold}, Top N: {final_top_n})")
        if final_documents:
            top_scores = [doc.metadata['rerank_score'] for doc in final_documents[:3]]
            logger.info(f"📊 Top 3 scores post-filtro: {[round(s, 4) for s in top_scores]}")
        
        return final_documents

# Instanciar el reranker como un singleton
reranker = Reranker()
