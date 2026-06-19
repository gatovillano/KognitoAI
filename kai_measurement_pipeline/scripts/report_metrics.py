import pandas as pd
from pathlib import Path

METRICS_PATH = Path(__file__).parent.parent / "results" / "metrics_summary.csv"
REPORT_PATH = Path(__file__).parent.parent / "results" / "report.md"

def main():
    df = pd.read_csv(METRICS_PATH)
    with open(REPORT_PATH, "w") as f:
        f.write("# Resumen de Métricas de Kognito AI\n\n")
        for _, row in df.iterrows():
            f.write(f"- **{row['metric']}**: {row['value']}\n")
    print(f"Reporte generado en {REPORT_PATH}")

if __name__ == "__main__":
    main()
