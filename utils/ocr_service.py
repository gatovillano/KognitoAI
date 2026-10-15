# utils/ocr_service.py

"""
Módulo de OCR local liviano para procesamiento de documentos escaneados y fotocopias.
Utiliza RapidOCR basado en ONNX Runtime con soporte prioritario para aceleración por GPU (CUDA),
carga dinámica de bibliotecas NVIDIA, bajo consumo de memoria página a página y logs detallados
de progreso y tiempo estimado (ETA) para documentos extensos.
"""

import asyncio
import ctypes
import glob
import logging
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Instancia global singleton para evitar recargar modelos ONNX en cada petición
_rapid_ocr_instance = None
_ocr_device = "cpu"
_nvidia_libs_loaded = False


def _ensure_nvidia_libraries_loaded() -> bool:
    """
    Carga dinámicamente las bibliotecas compartidas de NVIDIA instaladas vía pip
    (cublas, cudnn, curand, etc.) en el espacio de memoria del proceso usando ctypes.
    Esto permite que ONNX Runtime active CUDAExecutionProvider de forma fiable sin
    depender de variables de entorno del sistema operativo.
    """
    global _nvidia_libs_loaded
    if _nvidia_libs_loaded:
        return True

    try:
        loaded_count = 0
        site_packages = [p for p in sys.path if "site-packages" in p]
        for sp in site_packages:
            nvidia_root = os.path.join(sp, "nvidia")
            if not os.path.exists(nvidia_root):
                continue

            for root, _, files in os.walk(nvidia_root):
                if "lib" in root:
                    for f in sorted(files):
                        if ".so" in f:
                            try:
                                full_lib_path = os.path.join(root, f)
                                ctypes.CDLL(full_lib_path, mode=ctypes.RTLD_GLOBAL)
                                loaded_count += 1
                            except Exception:
                                pass

        if loaded_count > 0:
            logger.info(f"Cargadas {loaded_count} bibliotecas NVIDIA en memoria para aceleración GPU.")
        _nvidia_libs_loaded = True
        return True
    except Exception as e:
        logger.warning(f"No se pudieron precargar bibliotecas NVIDIA vía ctypes: {e}")
        return False


def is_local_ocr_available() -> bool:
    """Comprueba si el motor RapidOCR está disponible en el entorno."""
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        return True
    except ImportError:
        return False


def is_cuda_available() -> bool:
    """Comprueba si ONNX Runtime tiene disponibles proveedores CUDA o TensorRT."""
    try:
        _ensure_nvidia_libraries_loaded()
        import onnxruntime as ort
        providers = ort.get_available_providers()
        return "CUDAExecutionProvider" in providers or "TensorrtExecutionProvider" in providers
    except Exception:
        return False


def get_ocr_device() -> str:
    """Retorna el dispositivo actualmente configurado para OCR ('cuda' o 'cpu')."""
    return _ocr_device


def _get_ocr_engine():
    """Obtiene o inicializa de forma diferida el motor RapidOCR con GPU si está disponible."""
    global _rapid_ocr_instance, _ocr_device
    if _rapid_ocr_instance is None:
        try:
            from rapidocr_onnxruntime import RapidOCR

            _ensure_nvidia_libraries_loaded()

            if is_cuda_available():
                try:
                    logger.info("⚡ Inicializando RapidOCR con aceleración por GPU (CUDAExecutionProvider)...")
                    _rapid_ocr_instance = RapidOCR(
                        Det={"use_cuda": True},
                        Cls={"use_cuda": True},
                        Rec={"use_cuda": True}
                    )
                    _ocr_device = "cuda"
                    logger.info("✅ Motor RapidOCR con GPU CUDA inicializado exitosamente.")
                    return _rapid_ocr_instance
                except Exception as cuda_err:
                    logger.warning(
                        f"Fallo al inicializar RapidOCR con CUDA ({cuda_err}). Realizando fallback a CPU..."
                    )

            logger.info("Inicializando RapidOCR en CPU...")
            # Limitar hilos internos en CPU para no ahogar el procesador
            _rapid_ocr_instance = RapidOCR(
                Global={"intra_op_num_threads": 2, "inter_op_num_threads": 2}
            )
            _ocr_device = "cpu"
            logger.info("Motor RapidOCR inicializado correctamente en CPU.")
        except Exception as e:
            logger.error(f"Error al inicializar motor RapidOCR: {e}", exc_info=True)
            _rapid_ocr_instance = None
            _ocr_device = "unknown"
    return _rapid_ocr_instance


def _format_eta(seconds: float) -> str:
    """Formatea una duración en segundos a una cadena legible (ej. 2m 15s)."""
    if seconds < 0 or seconds != seconds:  # NaN o negativo
        return "calculando..."
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h {mins}m"


def _process_image_sync(
    image_bytes: bytes,
    min_confidence: float = 0.4
) -> Tuple[str, float, List[Dict[str, Any]]]:
    """
    Función síncrona que ejecuta el OCR sobre bytes de imagen.
    """
    engine = _get_ocr_engine()
    if not engine:
        return "", 0.0, []

    try:
        result, elapse = engine(image_bytes)
        if not result:
            return "", 0.0, []

        extracted_lines: List[str] = []
        confidences: List[float] = []
        detailed_boxes: List[Dict[str, Any]] = []

        # Ordenar líneas principalmente de arriba a abajo (coordenada Y), luego de izquierda a derecha (coordenada X)
        def _get_box_y(item):
            box = item[0]
            return min(pt[1] for pt in box)

        sorted_results = sorted(result, key=_get_box_y)

        for item in sorted_results:
            box, text, score = item[0], item[1], float(item[2])
            text_clean = text.strip()
            if text_clean and score >= min_confidence:
                extracted_lines.append(text_clean)
                confidences.append(score)
                detailed_boxes.append({
                    "text": text_clean,
                    "confidence": score,
                    "box": box
                })

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        full_text = "\n".join(extracted_lines)
        return full_text, avg_confidence, detailed_boxes

    except Exception as e:
        logger.error(f"Error durante procesamiento de OCR: {e}", exc_info=True)
        return "", 0.0, []


async def ocr_image_bytes(
    image_bytes: bytes,
    min_confidence: float = 0.4
) -> Tuple[str, float]:
    """
    Ejecuta OCR sobre una imagen (bytes) de manera asíncrona.
    Retorna el texto extraído y el puntaje de confianza promedio (0.0 a 1.0).
    """
    if not is_local_ocr_available():
        logger.warning("RapidOCR no está instalado en el sistema.")
        return "", 0.0

    full_text, avg_conf, _ = await asyncio.to_thread(_process_image_sync, image_bytes, min_confidence)
    return full_text, avg_conf


def _process_pdf_sync(
    pdf_bytes: bytes,
    dpi: int = 150,
    min_confidence: float = 0.4,
    progress_sync_cb: Optional[Callable[[int, int, float, str], None]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Renderiza y procesa un PDF página por página de forma secuencial y en *streaming* de memoria.
    No precarga todas las páginas a la vez, liberando la memoria tras cada página y emitiendo
    logs continuos con progreso y tiempo estimado (ETA).
    """
    import fitz  # PyMuPDF

    engine = _get_ocr_engine()
    if not engine:
        return "", {"error": "OCR engine not available"}

    full_pages_text: List[str] = []
    total_confidences: List[float] = []
    page_durations: List[float] = []

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            total_pages = len(doc)
            device_name = get_ocr_device()

            logger.info(
                f"🚀 [OCR INICIO] Comenzando procesamiento de PDF de {total_pages} páginas. "
                f"DPI: {dpi} | Dispositivo: {device_name.upper()}"
            )

            start_total_time = time.perf_counter()

            for page_idx in range(total_pages):
                page_start_time = time.perf_counter()
                current_page_num = page_idx + 1
                percent = (current_page_num / total_pages) * 100.0

                logger.info(
                    f"📄 [OCR] [{current_page_num}/{total_pages} - {percent:.1f}%] "
                    f"Procesando página {current_page_num}..."
                )

                try:
                    # 1. Renderizar SOLO la página actual (ahorra GB de RAM en PDFs largos)
                    page = doc[page_idx]
                    pix = page.get_pixmap(dpi=dpi)
                    img_bytes = pix.tobytes("png")
                    del pix  # Liberar memoria de imagen de inmediato

                    # 2. Ejecutar OCR
                    page_text, page_conf, _ = _process_image_sync(img_bytes, min_confidence)
                    del img_bytes

                    if page_text:
                        full_pages_text.append(f"--- Página {current_page_num} ---\n{page_text}")
                        if page_conf > 0:
                            total_confidences.append(page_conf)

                    page_elapsed = time.perf_counter() - page_start_time
                    page_durations.append(page_elapsed)

                    # 3. Calcular ETA basado en el promedio de páginas ya procesadas
                    avg_page_time = sum(page_durations) / len(page_durations)
                    remaining_pages = total_pages - current_page_num
                    eta_seconds = avg_page_time * remaining_pages
                    eta_str = _format_eta(eta_seconds)

                    lines_count = len(page_text.splitlines()) if page_text else 0
                    logger.info(
                        f"✅ [OCR] [{current_page_num}/{total_pages} - {percent:.1f}%] "
                        f"Página completada en {page_elapsed:.2f}s | "
                        f"Líneas: {lines_count} | Confianza: {page_conf*100:.1f}% | "
                        f"Restante est. (ETA): {eta_str}"
                    )

                    if progress_sync_cb:
                        try:
                            progress_sync_cb(current_page_num, total_pages, percent, eta_str)
                        except Exception as cb_err:
                            logger.debug(f"Error en callback de progreso de OCR: {cb_err}")

                except Exception as page_err:
                    logger.error(
                        f"❌ [OCR] Error procesando página {current_page_num}/{total_pages}: {page_err}",
                        exc_info=True
                    )

            total_elapsed = time.perf_counter() - start_total_time
            avg_conf = sum(total_confidences) / len(total_confidences) if total_confidences else 0.0
            final_text = "\n\n".join(full_pages_text).strip()

            logger.info(
                f"🎉 [OCR COMPLETADO] Documento de {total_pages} páginas finalizado con éxito en "
                f"{_format_eta(total_elapsed)} ({total_elapsed:.1f}s total). "
                f"Páginas con texto: {len(full_pages_text)}/{total_pages} | "
                f"Confianza global promedio: {avg_conf*100:.1f}%"
            )

            stats = {
                "total_pages": total_pages,
                "pages_with_text": len(full_pages_text),
                "avg_confidence": avg_conf,
                "engine": "rapidocr_onnxruntime",
                "device": get_ocr_device(),
                "total_elapsed_seconds": round(total_elapsed, 2)
            }
            return final_text, stats

    except Exception as e:
        logger.error(f"Error general procesando PDF para OCR local: {e}", exc_info=True)
        return "", {"error": str(e)}


async def ocr_pdf_bytes(
    pdf_bytes: bytes,
    dpi: int = 150,
    min_confidence: float = 0.4,
    progress_callback: Optional[Callable[[int, int, float, str], Any]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Ejecuta OCR sobre un archivo PDF escaneado (bytes) de manera asíncrona.
    Permite un callback de progreso para emitir eventos de WebSocket hacia el frontend.
    """
    if not is_local_ocr_available():
        logger.warning("RapidOCR no está instalado en el sistema.")
        return "", {"error": "RapidOCR not installed"}

    loop = asyncio.get_running_loop()

    def _sync_cb_bridge(curr: int, tot: int, pct: float, eta: str):
        if progress_callback:
            if asyncio.iscoroutinefunction(progress_callback):
                asyncio.run_coroutine_threadsafe(progress_callback(curr, tot, pct, eta), loop)
            else:
                progress_callback(curr, tot, pct, eta)

    return await asyncio.to_thread(_process_pdf_sync, pdf_bytes, dpi, min_confidence, _sync_cb_bridge)
