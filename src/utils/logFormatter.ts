// src/utils/logFormatter.ts

export function formatDetailedLog(logContent: string): { summary: string; fullContent: string; isDetailed: boolean } {
  const lines = logContent.split('\n');
  const detailedPatterns = [
    /^(kognito_core|kognito_db)\s*\|\s*.*$/, // Líneas que empiezan con kognito_core | o kognito_db |
    /^\s*╭─+ locals -+╮\s*$/, // Bloque de locals
    /^\s*TypeError:\s*/, // Errores de tipo
    /^\s*ValueError:\s*/, // Errores de valor
    /^\s*Exception:\s*/, // Excepciones genéricas
    /.*in arun/, // Patrón común en trazas de Langchain
    /.*in _arun/,
    /.*❱\s*\d+\s*\|/, // Líneas que indican código fuente
  ];

  const isDetailed = detailedPatterns.some(pattern => lines.some(line => pattern.test(line)));

  if (!isDetailed) {
    return { summary: logContent, fullContent: logContent, isDetailed: false };
  }

  let summary = "Log detallado (clic para expandir):\n";
  let foundRelevantLine = false;

  for (const line of lines) {
    const trimmedLine = line.trim();

    if (trimmedLine.includes("TypeError:") || trimmedLine.includes("Error:") || trimmedLine.includes("Exception:")) {
      summary += "  " + trimmedLine.replace(/^(kognito_core|kognito_db)\s*\|\s*/, '') + "\n";
      foundRelevantLine = true;
      break; // Solo la primera línea de error
    }
    if (trimmedLine.includes("LOG:") && !foundRelevantLine) {
      summary += "  " + trimmedLine.replace(/^(kognito_db)\s*\|\s*/, '') + "\n";
      foundRelevantLine = true;
      break; // Solo la primera línea LOG
    }
    if (trimmedLine.includes("checkpoint") && !foundRelevantLine) {
      summary += "  " + trimmedLine.replace(/^(kognito_db)\s*\|\s*/, '') + "\n";
      foundRelevantLine = true;
      break; // Solo la primera línea de checkpoint
    }
  }

  if (!foundRelevantLine) {
    // Si no se encontró una línea específica, tomar las primeras líneas relevantes
    let briefLines = [];
    for(let i = 0; i < lines.length && briefLines.length < 3; i++) {
        const line = lines[i];
        if (line.trim() && !line.includes('─') && !line.includes('│')) {
            briefLines.push(line.trim().replace(/^(kognito_core|kognito_db)\s*\|\s*/, ''));
        }
    }
    summary += briefLines.join('\n');
  }

  return { summary, fullContent: logContent, isDetailed: true };
}