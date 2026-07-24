"""
Ejemplo: Pipeline completo de investigación antropológica
Demuestra el uso de KAI-Ethno para una investigación bibliográfica sistemática
"""

import asyncio
import argparse
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_research_pipeline(
    query: str,
    max_sources: int = 50,
    year_start: int = 2020,
    year_end: int = 2025,
    output_dir: str = "./output",
    include_visualizations: bool = True,
    generate_document: bool = True,
):
    """
    Ejecuta el pipeline completo de investigación.

    Args:
        query: Pregunta o tema de investigación
        max_sources: Número máximo de fuentes a recolectar
        year_start: Año inicial del rango
        year_end: Año final del rango
        output_dir: Directorio de salida
        include_visualizations: Generar visualizaciones
        generate_document: Generar documento académico
    """
    # Importar orquestador
    from orchestrator import KAIEthnoOrchestrator

    logger.info(f"Iniciando investigación: '{query}'")
    logger.info(f"Rango de años: {year_start}-{year_end}")
    logger.info(f"Max fuentes: {max_sources}")

    # Crear orquestador
    orchestrator = KAIEthnoOrchestrator(
        enable_ethics=True,
        enable_memory=True,
        output_dir=output_dir,
    )

    try:
        # Ejecutar pipeline
        results = await orchestrator.run_research(
            research_question=query,
            max_sources=max_sources,
            year_range=(year_start, year_end),
            include_visualizations=include_visualizations,
            generate_document=generate_document,
            document_type="literature_review",
            citation_style="apa",
        )

        # Mostrar resultados
        print("\n" + "=" * 60)
        print("RESULTADOS DE LA INVESTIGACIÓN")
        print("=" * 60)

        print(f"\n📊 Estado: {results['status']}")
        print(f"📚 Fuentes recolectadas: {results.get('sources_count', 0)}")
        print(f"⏱️  Tiempo de ejecución: {results.get('execution_time', 0):.2f}s")

        # Mostrar etapas
        if "stages" in results:
            print("\n📋 Etapas completadas:")
            for stage, data in results["stages"].items():
                if isinstance(data, dict):
                    status = data.get("status", "completada")
                    print(f"  - {stage}: {status}")

        # Mostrar ruta de salida
        output_path = Path(output_dir)
        print(f"\n📁 Resultados guardados en: {output_path.absolute()}")

        # Mostrar archivos generados
        if output_path.exists():
            files = list(output_path.rglob("*"))
            if files:
                print("\n📄 Archivos generados:")
                for f in files[:10]:  # Mostrar primeros 10
                    print(f"  - {f.relative_to(output_path)}")

        print("\n" + "=" * 60)

        return results

    except Exception as e:
        logger.error(f"Error en el pipeline: {e}", exc_info=True)
        raise
    finally:
        # Cerrar recursos
        await orchestrator.shutdown()


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="KAI-Ethno: Investigación Antropológica Aumentada"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Pregunta o tema de investigación",
    )
    parser.add_argument(
        "--max-sources",
        type=int,
        default=50,
        help="Número máximo de fuentes a recolectar (default: 50)",
    )
    parser.add_argument(
        "--year-start",
        type=int,
        default=2020,
        help="Año inicial del rango (default: 2020)",
    )
    parser.add_argument(
        "--year-end",
        type=int,
        default=2025,
        help="Año final del rango (default: 2025)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="Directorio de salida (default: ./output)",
    )
    parser.add_argument(
        "--no-visualizations",
        action="store_true",
        help="No generar visualizaciones",
    )
    parser.add_argument(
        "--no-document",
        action="store_true",
        help="No generar documento académico",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar logs detallados",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Ejecutar pipeline
    asyncio.run(
        run_research_pipeline(
            query=args.query,
            max_sources=args.max_sources,
            year_start=args.year_start,
            year_end=args.year_end,
            output_dir=args.output,
            include_visualizations=not args.no_visualizations,
            generate_document=not args.no_document,
        )
    )


if __name__ == "__main__":
    main()
