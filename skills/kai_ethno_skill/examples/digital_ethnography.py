"""
Ejemplo: Etnografía digital
Demuestra el análisis de transcripciones de entrevistas con detección de PII,
codificación temática (Braun & Clarke) y generación de insights cualitativos
"""

import asyncio
import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DigitalEthnographyAnalyzer:
    """Analizador de etnografía digital"""

    def __init__(self, output_dir: str = "./ethnography_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Importar agentes
        from agents.ethnograph import EthnographAgent
        from agents.pattern_finder import PatternFinderAgent
        from agents.synthesizer import SynthesizerAgent
        from agents.visualizer import VisualizerAgent

        self.ethnograph = EthnographAgent()
        self.pattern_finder = PatternFinderAgent()
        self.synthesizer = SynthesizerAgent()
        self.visualizer = VisualizerAgent()

    async def analyze_transcripts(
        self,
        transcript_dir: str,
        anonymize: bool = True,
        language: str = "es",
    ) -> Dict[str, Any]:
        """
        Analiza transcripciones de entrevistas/grupos focales.

        Args:
            transcript_dir: Directorio con archivos de transcripción (.txt, .md, .json)
            anonymize: Anonimizar PII automáticamente
            language: Idioma de las transcripciones (es, en, pt)

        Returns:
            Diccionario con resultados del análisis
        """
        transcript_path = Path(transcript_dir)
        if not transcript_path.exists():
            raise FileNotFoundError(f"Directorio no encontrado: {transcript_dir}")

        # Cargar transcripciones
        transcripts = self._load_transcripts(transcript_path)
        logger.info(f"Cargadas {len(transcripts)} transcripciones")

        results = {
            "transcript_count": len(transcripts),
            "language": language,
            "anonymized": anonymize,
            "stages": {},
        }

        # Etapa 1: Procesamiento etnográfico
        logger.info("Etapa 1: Procesamiento etnográfico")
        processed = await self.ethnograph.process_corpus(
            sources={"documents": transcripts},
            language=language,
            anonymize_pii=anonymize,
        )
        results["stages"]["ethnographic"] = processed

        # Etapa 2: Minería de patrones
        logger.info("Etapa 2: Minería de patrones")
        patterns = await self.pattern_finder.analyze(processed)
        results["stages"]["patterns"] = patterns

        # Etapa 3: Síntesis cualitativa
        logger.info("Etapa 3: Síntesis cualitativa")
        synthesis = await self.synthesizer.synthesize(
            patterns,
            sources={"documents": transcripts},
            synthesis_type="grounded_theory",
        )
        results["stages"]["synthesis"] = synthesis

        # Etapa 4: Visualizaciones
        logger.info("Etapa 4: Generando visualizaciones")
        viz_data = {
            "keywords": patterns.get("keywords", {}),
            "networks": patterns.get("networks", []),
            "clusters": patterns.get("clusters", []),
            "themes": synthesis.get("themes", []),
        }
        visualizations = await self.visualizer.run(viz_data)
        results["stages"]["visualizations"] = visualizations

        # Guardar resultados
        self._save_results(results)

        return results

    def _load_transcripts(self, directory: Path) -> List[Dict[str, Any]]:
        """Carga todas las transcripciones del directorio"""
        transcripts = []
        extensions = {".txt", ".md", ".json"}

        for file_path in directory.rglob("*"):
            if file_path.suffix.lower() in extensions and file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8")

                    # Determinar formato
                    if file_path.suffix == ".json":
                        data = json.loads(content)
                        # Asumir que es una lista de segmentos o un documento
                        if isinstance(data, list):
                            # Lista de segmentos de entrevista
                            full_text = " ".join(
                                segment.get("text", "") for segment in data
                            )
                            transcripts.append(
                                {
                                    "id": file_path.stem,
                                    "text": full_text,
                                    "segments": data,
                                    "source_file": str(file_path),
                                }
                            )
                        else:
                            transcripts.append(
                                {
                                    "id": file_path.stem,
                                    "text": data.get("text", str(data)),
                                    "source_file": str(file_path),
                                }
                            )
                    else:
                        # Archivo de texto plano
                        transcripts.append(
                            {
                                "id": file_path.stem,
                                "text": content,
                                "source_file": str(file_path),
                            }
                        )

                    logger.debug(f"Cargado: {file_path.name}")

                except Exception as e:
                    logger.error(f"Error cargando {file_path}: {e}")

        return transcripts

    def _save_results(self, results: Dict[str, Any]):
        """Guarda resultados en archivos"""
        import json
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Guardar JSON completo
        json_path = self.output_dir / f"ethnography_analysis_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # Guardar resumen en Markdown
        md_path = self.output_dir / f"ethnography_summary_{timestamp}.md"
        self._generate_markdown_summary(results, md_path)

        # Guardar citas relevantes
        quotes_path = self.output_dir / f"ethnography_quotes_{timestamp}.txt"
        self._save_key_quotes(results, quotes_path)

        logger.info(f"Resultados guardados en: {self.output_dir}")

    def _generate_markdown_summary(self, results: Dict[str, Any], output_path: Path):
        """Genera resumen en Markdown"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Informe de Etnografía Digital\n\n")
            f.write(
                f"**Fecha:** {results.get('timestamp', 'N/A')}\n"
            )
            f.write(
                f"**Transcripciones analizadas:** {results.get('transcript_count', 0)}\n"
            )
            f.write(
                f"**Idioma:** {results.get('language', 'N/A')}\n\n"
            )

            # Temas principales
            if "synthesis" in results.get("stages", {}):
                synthesis = results["stages"]["synthesis"]
                f.write("## Temas Principales\n\n")
                themes = synthesis.get("themes", [])
                for i, theme in enumerate(themes, 1):
                    f.write(f"{i}. **{theme.get('name', 'Tema')}**\n")
                    f.write(f"   - {theme.get('description', 'Sin descripción')}\n")
                    f.write(
                        f"   - Frecuencia: {theme.get('frequency', 'N/A')}\n\n"
                    )

            # Categorías de codificación
            if "ethnographic" in results.get("stages", {}):
                ethno = results["stages"]["ethnographic"]
                f.write("## Categorías de Codificación\n\n")
                codes = ethno.get("codes", {})
                for code, count in codes.items():
                    f.write(f"- **{code}**: {count} menciones\n")

            # Patrones detectados
            if "patterns" in results.get("stages", {}):
                patterns = results["stages"]["patterns"]
                f.write("\n## Patrones Detectados\n\n")
                keywords = patterns.get("keywords", {})
                for word, freq in list(keywords.items())[:10]:
                    f.write(f"- {word}: {freq}\n")

    def _save_key_quotes(self, results: Dict[str, Any], output_path: Path):
        """Extrae y guarda citas relevantes"""
        quotes = []

        # Extraer de resultados etnográficos
        if "ethnographic" in results.get("stages", {}):
            ethno = results["stages"]["ethnographic"]
            segments = ethno.get("segments", [])
            for segment in segments:
                if isinstance(segment, dict) and segment.get("importance", 0) > 0.7:
                    quotes.append(segment.get("text", ""))

        # Extraer de síntesis
        if "synthesis" in results.get("stages", {}):
            synthesis = results["stages"]["synthesis"]
            key_insights = synthesis.get("key_insights", [])
            for insight in key_insights:
                if isinstance(insight, dict):
                    quotes.append(insight.get("quote", ""))

        # Guardar
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Citas Relevantes\n\n")
            for i, quote in enumerate(quotes, 1):
                f.write(f"{i}. > {quote}\n\n")

    async def interactive_session(self, transcript_dir: str):
        """
        Sesión interactiva para análisis progresivo.
        Permite agregar transcripciones y ver resultados en tiempo real.
        """
        logger.info("Iniciando sesión interactiva de etnografía digital")
        logger.info(f"Directorio de transcripciones: {transcript_dir}")

        transcript_path = Path(transcript_dir)
        if not transcript_path.exists():
            logger.error(f"Directorio no encontrado: {transcript_dir}")
            return

        # Cargar transcripciones existentes
        transcripts = self._load_transcripts(transcript_path)
        logger.info(f"Transcripciones cargadas: {len(transcripts)}")

        if not transcripts:
            logger.warning("No se encontraron transcripciones")
            return

        # Menú interactivo
        while True:
            print("\n" + "=" * 50)
            print("ETNOGRAFÍA DIGITAL - MENÚ INTERACTIVO")
            print("=" * 50)
            print("1. Analizar transcripciones")
            print("2. Ver temas detectados")
            print("3. Ver códigos de análisis")
            print("4. Generar visualizaciones")
            print("5. Exportar informe")
            print("6. Salir")
            print("=" * 50)

            choice = input("\nSelecciona una opción (1-6): ").strip()

            if choice == "1":
                await self._run_full_analysis(transcripts)
            elif choice == "2":
                self._show_themes()
            elif choice == "3":
                self._show_codes()
            elif choice == "4":
                await self._generate_visualizations()
            elif choice == "5":
                self._export_report()
            elif choice == "6":
                print("Saliendo...")
                break
            else:
                print("Opción inválida")

    async def _run_full_analysis(self, transcripts: List[Dict[str, Any]]):
        """Ejecuta análisis completo"""
        print("\nEjecutando análisis completo...")
        results = await self.analyze_transcripts(
            transcript_dir=str(Path(transcripts[0]["source_file"]).parent),
        )
        print(f"\n✅ Análisis completado")
        print(f"   - Transcripciones: {results['transcript_count']}")
        if "stages" in results:
            print(f"   - Etapas: {', '.join(results['stages'].keys())}")

    def _show_themes(self):
        """Muestra temas detectados (placeholder)"""
        print("\nTemas detectados:")
        print("  (Requiere ejecutar análisis primero)")

    def _show_codes(self):
        """Muestra códigos de análisis (placeholder)"""
        print("\nCódigos de análisis:")
        print("  (Requiere ejecutar análisis primero)")

    async def _generate_visualizations(self):
        """Genera visualizaciones (placeholder)"""
        print("\nGenerando visualizaciones...")
        print("  (Requiere ejecutar análisis primero)")

    def _export_report(self):
        """Exporta informe (placeholder)"""
        print("\nExportando informe...")
        print(f"   (Los informes se guardan automáticamente en: {self.output_dir})")


async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="KAI-Ethno: Análisis de Etnografía Digital"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Directorio con transcripciones (.txt, .md, .json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./ethnography_output",
        help="Directorio de salida (default: ./ethnography_output)",
    )
    parser.add_argument(
        "--no-anonymize",
        action="store_true",
        help="No anonimizar PII",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="es",
        choices=["es", "en", "pt"],
        help="Idioma de las transcripciones (default: es)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Modo interactivo",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar logs detallados",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    analyzer = DigitalEthnographyAnalyzer(output_dir=args.output)

    try:
        if args.interactive:
            await analyzer.interactive_session(args.input)
        else:
            results = await analyzer.analyze_transcripts(
                transcript_dir=args.input,
                anonymize=not args.no_anonymize,
                language=args.language,
            )

            # Mostrar resumen
            print("\n" + "=" * 60)
            print("ANÁLISIS DE ETNOGRAFÍA DIGITAL COMPLETADO")
            print("=" * 60)
            print(f"\n📊 Transcripciones analizadas: {results['transcript_count']}")
            print(f"🔒 Anonimización: {'Activada' if results['anonymized'] else 'Desactivada'}")
            print(f"🌐 Idioma: {results['language']}")

            # Mostrar temas
            if "synthesis" in results.get("stages", {}):
                themes = results["stages"]["synthesis"].get("themes", [])
                if themes:
                    print(f"\n🎯 Temas detectados: {len(themes)}")
                    for i, theme in enumerate(themes[:5], 1):
                        print(f"   {i}. {theme.get('name', 'Sin nombre')}")

            # Mostrar códigos
            if "ethnographic" in results.get("stages", {}):
                codes = results["stages"]["ethnographic"].get("codes", {})
                if codes:
                    print(f"\n🏷️  Códigos de análisis: {len(codes)}")
                    for code, count in list(codes.items())[:5]:
                        print(f"   - {code}: {count}")

            print(f"\n📁 Resultados guardados en: {Path(args.output).absolute()}")
            print("=" * 60)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
