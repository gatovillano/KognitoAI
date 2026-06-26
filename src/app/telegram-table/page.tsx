"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";

interface TableData {
  headers: string[];
  rows: string[][];
  title?: string;
}

function TableViewer() {
  const searchParams = useSearchParams();
  const [tableData, setTableData] = useState<TableData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const rawData = searchParams.get("data");
    if (!rawData) {
      setError("No se proporcionaron datos para la tabla.");
      return;
    }

    try {
      // Decodificar Base64 URL Safe de forma segura para UTF-8
      const base64 = rawData.replace(/-/g, "+").replace(/_/g, "/");
      const decodedStr = atob(base64);
      
      // Decodificar caracteres multibyte (UTF-8)
      const bytes = new Uint8Array(decodedStr.length);
      for (let i = 0; i < decodedStr.length; i++) {
        bytes[i] = decodedStr.charCodeAt(i);
      }
      const decoder = new TextDecoder("utf-8");
      const decodedJson = decoder.decode(bytes);
      
      const parsed = JSON.parse(decodedJson);

      if (parsed && Array.isArray(parsed.headers) && Array.isArray(parsed.rows)) {
        setTableData(parsed);
      } else {
        setError("El formato de la tabla no es válido.");
      }
    } catch (err) {
      console.error("Error decodificando la tabla:", err);
      setError("Ocurrió un error al decodificar los datos de la tabla.");
    }
  }, [searchParams]);

  // Exportar a CSV
  const handleExportCSV = () => {
    if (!tableData) return;
    const csvContent = [
      tableData.headers.join(","),
      ...tableData.rows.map((row) =>
        row.map((val) => `"${val.replace(/"/g, '""')}"`).join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${tableData.title || "tabla"}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Copiar al portapapeles en formato TSV
  const handleCopyToClipboard = () => {
    if (!tableData) return;
    const tsvContent = [
      tableData.headers.join("\t"),
      ...tableData.rows.map((row) => row.join("\t")),
    ].join("\n");

    navigator.clipboard.writeText(tsvContent).then(
      () => alert("¡Tabla copiada al portapapeles en formato TSV!"),
      () => alert("No se pudo copiar al portapapeles.")
    );
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-slate-950 text-slate-100 rounded-2xl border border-slate-800 shadow-2xl max-w-md mx-auto my-12">
        <span className="text-4xl mb-4">⚠️</span>
        <h2 className="text-xl font-bold mb-2">Error de Carga</h2>
        <p className="text-slate-400 text-center text-sm">{error}</p>
      </div>
    );
  }

  if (!tableData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] text-slate-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-4"></div>
        <p className="text-sm">Cargando visualizador de datos...</p>
      </div>
    );
  }

  // Filtrar filas según la búsqueda
  const filteredRows = tableData.rows.filter((row) =>
    row.some((cell) => cell.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-6 text-slate-100">
      <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-slate-800/60 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/30">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="text-xs font-semibold tracking-wider text-indigo-400 uppercase">
                Kognito AI • Tabla de Datos
              </span>
              <h1 className="text-2xl font-bold mt-1 bg-gradient-to-r from-white via-slate-200 to-indigo-200 bg-clip-text text-transparent">
                {tableData.title || "Visualizador de Datos"}
              </h1>
            </div>
            <div className="flex gap-2 text-xs">
              <button
                onClick={handleCopyToClipboard}
                className="px-3 py-2 bg-slate-800 hover:bg-slate-700 active:bg-slate-900 border border-slate-700/60 rounded-xl transition duration-200 flex items-center gap-1.5 font-medium"
              >
                📋 Copiar
              </button>
              <button
                onClick={handleExportCSV}
                className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 rounded-xl transition duration-200 flex items-center gap-1.5 font-medium text-white shadow-lg shadow-indigo-600/20"
              >
                📥 CSV
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div className="mt-5 relative">
            <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500 text-sm">
              🔍
            </span>
            <input
              type="text"
              placeholder="Buscar en la tabla..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-950/60 border border-slate-800 rounded-2xl text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
          </div>
        </div>

        {/* Table Viewport */}
        <div className="overflow-x-auto w-full">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-950/40 border-b border-slate-800/80">
                {tableData.headers.map((h, i) => (
                  <th
                    key={i}
                    className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {filteredRows.length > 0 ? (
                filteredRows.map((row, rowIndex) => (
                  <tr
                    key={rowIndex}
                    className="hover:bg-slate-800/25 transition duration-150 group"
                  >
                    {row.map((cell, colIndex) => (
                      <td
                        key={colIndex}
                        className="px-6 py-4 text-sm text-slate-300 font-medium group-hover:text-slate-100"
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={tableData.headers.length}
                    className="px-6 py-12 text-center text-slate-500 text-sm"
                  >
                    Ningún registro coincide con tu búsqueda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800/40 bg-slate-950/20 flex justify-between items-center text-xs text-slate-500 font-medium">
          <span>
            Mostrando {filteredRows.length} de {tableData.rows.length} registros
          </span>
          <span>Kognito AI</span>
        </div>
      </div>
    </div>
  );
}

export default function TelegramTablePage() {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center py-8">
      <Suspense fallback={
        <div className="flex flex-col items-center justify-center text-slate-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-4"></div>
          <p className="text-sm">Cargando...</p>
        </div>
      }>
        <TableViewer />
      </Suspense>
    </div>
  );
}
