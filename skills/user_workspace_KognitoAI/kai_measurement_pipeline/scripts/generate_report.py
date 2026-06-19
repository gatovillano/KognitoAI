#!/usr/bin/env python3
"""
Generate HTML Report for KAI Measurement
"""
import json
from datetime import datetime
from pathlib import Path

def generate_html_report(metrics: dict, output_path: str):
    """Generate HTML report"""
    
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KAI Measurement Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-slate-100 min-h-screen">
    <div class="container mx-auto p-6">
        <div class="max-w-4xl mx-auto">
            <!-- Header -->
            <div class="text-center mb-8">
                <h1 class="text-4xl font-bold text-slate-800 mb-2">
                    <i class="fas fa-brain text-indigo-600 mr-2"></i>
                    KAI Measurement Report
                </h1>
                <p class="text-slate-500">Generated: {datetime.now().strftime('%d de %B de %Y, %H:%M')}</p>
            </div>

            <!-- Summary Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div class="bg-white/60 backdrop-blur-md border border-slate-200 rounded-2xl shadow-xl p-5">
                    <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-indigo-500/20 to-purple-500/10 rounded-bl-full rounded-tr-xl"></div>
                    <p class="text-xs font-bold text-indigo-600 uppercase tracking-wider mb-1">Total Queries</p>
                    <p class="text-3xl font-black text-slate-800 mb-2">{metrics.get('total_queries', 0)}</p>
                </div>
                
                <div class="bg-white/60 backdrop-blur-md border border-slate-200 rounded-2xl shadow-xl p-5">
                    <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-emerald-500/20 to-teal-500/10 rounded-bl-full rounded-tr-xl"></div>
                    <p class="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1">Exitosas</p>
                    <p class="text-3xl font-black text-slate-800 mb-2">{metrics.get('successful', 0)}</p>
                </div>
                
                <div class="bg-white/60 backdrop-blur-md border border-slate-200 rounded-2xl shadow-xl p-5">
                    <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-violet-500/20 to-pink-500/10 rounded-bl-full rounded-tr-xl"></div>
                    <p class="text-xs font-bold text-violet-600 uppercase tracking-wider mb-1">Tasa de Éxito</p>
                    <p class="text-3xl font-black text-slate-800 mb-2">{metrics.get('success_rate', '0%')}</p>
                </div>
            </div>

            <!-- Categories -->
            <div class="bg-white/60 backdrop-blur-md border border-slate-200 rounded-2xl shadow-xl p-6 mb-6">
                <h2 class="text-xl font-bold text-slate-800 mb-4">
                    <i class="fas fa-chart-pie text-purple-600 mr-2"></i>
                    Categorías
                </h2>
                <div class="space-y-3">
    """
    
    for category, data in metrics.get('categories', {}).items():
        total = data.get('total', 0)
        correct = data.get('correct', 0)
        rate = (correct / total * 100) if total > 0 else 0
        
        html += f"""
                    <div class="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                        <span class="font-medium text-slate-700">{category}</span>
                        <span class="text-sm text-slate-500">{correct}/{total} correctas ({rate:.1f}%)</span>
                    </div>
        """
    
    html += """
                </div>
            </div>

            <!-- Footer -->
            <div class="text-center text-slate-400 text-sm">
                <p>KAI Measurement Pipeline - Kognito AI Labs SpA</p>
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    with open(output_path, 'w') as f:
        f.write(html)

if __name__ == "__main__":
    # Load metrics
    metrics_path = Path(__file__).parent.parent / "reports" / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            metrics = json.load(f)
        generate_html_report(metrics, str(metrics_path.parent / "report.html"))
        print("✅ Report generated!")
    else:
        print("No metrics found")
