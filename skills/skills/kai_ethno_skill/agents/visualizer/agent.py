"""
Visualizer Agent - Cartógrafo Visual
Agente especializado en representaciones visuales de datos
"""

import asyncio
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VisualizerState(BaseModel):
    """Estado del agente Visualizer"""
    data: Dict[str, Any] = Field(default_factory=dict)
    chart_type: str = "auto"
    generated_visuals: List[Dict[str, Any]] = Field(default_factory=list)
    export_formats: List[str] = Field(default_factory=lambda: ["png", "svg", "pdf"])
    status: str = "idle"


class VisualizerAgent:
    """
    Agente Visualizer - Especialista en visualización
    
    Capacidades:
    - Redes semánticas interactivas (D3.js, Plotly)
    - Visualización de redes Actor-Red (Gephi integration)
    - Mapas temáticos georreferenciados
    - Líneas de tiempo históricas
    - Diagramas de flujo metodológico
    - Infografías académicas
    """
    
    name = "visualizer"
    description = "Cartógrafo Visual - Representaciones visuales de datos"
    
    def __init__(self, llm_service: Any = None, output_dir: str = "./output/visualizations"):
        self.llm = llm_service
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.graph = self._build_graph()
        self.state = VisualizerState()
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para el flujo del agente"""
        
        def analyze_data(state: VisualizerState) -> Dict[str, Any]:
            """Analiza datos para determinar mejor visualización"""
            data = state.data
            viz_types = []
            
            # Decidir tipos de visualización según datos disponibles
            if data.get("keywords"):
                viz_types.append("wordcloud")
                viz_types.append("bar_chart")
            
            if data.get("networks") and data["networks"]:
                viz_types.append("network_graph")
            
            if data.get("temporal"):
                viz_types.append("timeline")
            
            if data.get("clusters"):
                viz_types.append("cluster_map")
            
            if data.get("synthesis", {}).get("triangulation"):
                viz_types.append("triangulation_matrix")
            
            if not viz_types:
                viz_types = ["summary_dashboard"]
            
            return {"status": "analyzed", "recommended_types": viz_types}
        
        def generate_visualization(state: VisualizerState) -> Dict[str, Any]:
            """Genera visualización según tipo de dato"""
            visuals = []
            viz_types = state.data.get("recommended_types", ["summary_dashboard"])
            
            for viz_type in viz_types:
                try:
                    if viz_type == "wordcloud":
                        visuals.append(self._create_wordcloud(state.data.get("keywords", {})))
                    elif viz_type == "bar_chart":
                        visuals.append(self._create_bar_chart(state.data.get("keywords", {})))
                    elif viz_type == "network_graph":
                        visuals.append(self._create_network_graph(state.data.get("networks", [])))
                    elif viz_type == "timeline":
                        visuals.append(self._create_timeline(state.data.get("temporal", {})))
                    elif viz_type == "cluster_map":
                        visuals.append(self._create_cluster_map(state.data.get("clusters", [])))
                    elif viz_type == "triangulation_matrix":
                        visuals.append(self._create_triangulation_matrix(state.data.get("synthesis", {})))
                    elif viz_type == "summary_dashboard":
                        visuals.append(self._create_summary_dashboard(state.data))
                except Exception as e:
                    logger.error(f"Error generando {viz_type}: {e}")
            
            return {"status": "generated", "generated_visuals": visuals}
        
        def optimize_layout(state: VisualizerState) -> Dict[str, Any]:
            """Optimiza layout y legibilidad"""
            # En una implementación completa, aquí se ajustarían parámetros de layout
            return {"status": "optimized"}
        
        def export_visuals(state: VisualizerState) -> Dict[str, Any]:
            """Exporta en múltiples formatos"""
            exported = []
            for viz in state.generated_visuals:
                viz_info = {
                    "type": viz.get("type"),
                    "title": viz.get("title"),
                    "files": {}
                }
                
                base_path = viz.get("path", "")
                if base_path:
                    for fmt in state.export_formats:
                        fmt_path = f"{base_path}.{fmt}"
                        viz_info["files"][fmt] = fmt_path
                
                exported.append(viz_info)
            
            return {"status": "exported", "exported_visuals": exported}
        
        workflow = StateGraph(VisualizerState)
        
        workflow.add_node("analyze", analyze_data)
        workflow.add_node("generate", generate_visualization)
        workflow.add_node("optimize", optimize_layout)
        workflow.add_node("export", export_visuals)
        
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "generate")
        workflow.add_edge("generate", "optimize")
        workflow.add_edge("optimize", "export")
        workflow.add_edge("export", END)
        
        return workflow.compile()
    
    async def run(self, data: Dict[str, Any], chart_type: str = "auto") -> Dict[str, Any]:
        """Ejecuta el agente con datos para visualizar"""
        self.state.data = data
        self.state.chart_type = chart_type
        self.state.status = "running"
        
        try:
            result = await self.graph.ainvoke(self.state)
            self.state = VisualizerState(**result)
            return {
                "status": "success",
                "visuals": self.state.generated_visuals,
                "formats": self.state.export_formats,
                "output_dir": self.output_dir
            }
        except Exception as e:
            self.state.status = "error"
            logger.error(f"Error en Visualizer: {e}")
            return {"status": "error", "error": str(e)}
    
    def _create_wordcloud(self, keywords: Dict[str, int]) -> Dict[str, Any]:
        """Crea nube de palabras"""
        try:
            import matplotlib.pyplot as plt
            from wordcloud import WordCloud
            
            if not keywords:
                return {"type": "wordcloud", "error": "No keywords provided"}
            
            wc = WordCloud(
                width=800, height=400,
                background_color="white",
                max_words=100,
                colormap="viridis"
            ).generate_from_frequencies(keywords)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.output_dir, f"wordcloud_{timestamp}")
            wc.to_file(f"{path}.png")
            
            return {
                "type": "wordcloud",
                "title": "Nube de Palabras - Términos Clave",
                "path": path,
                "top_terms": list(keywords.items())[:10]
            }
        except ImportError:
            logger.warning("wordcloud no instalado, saltando visualización")
            return {"type": "wordcloud", "error": "wordcloud library not installed"}
        except Exception as e:
            logger.error(f"Error en wordcloud: {e}")
            return {"type": "wordcloud", "error": str(e)}
    
    def _create_bar_chart(self, keywords: Dict[str, int]) -> Dict[str, Any]:
        """Crea gráfico de barras de frecuencias"""
        try:
            import matplotlib.pyplot as plt
            
            if not keywords:
                return {"type": "bar_chart", "error": "No keywords provided"}
            
            sorted_kw = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:20]
            terms = [k for k, v in sorted_kw]
            values = [v for k, v in sorted_kw]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(terms[::-1], values[::-1], color="steelblue")
            ax.set_xlabel("Frecuencia")
            ax.set_title("Top 20 Términos - Frecuencia en Corpus")
            ax.grid(axis="x", alpha=0.3)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.output_dir, f"bar_chart_{timestamp}")
            plt.tight_layout()
            plt.savefig(f"{path}.png", dpi=150)
            plt.savefig(f"{path}.svg")
            plt.close()
            
            return {
                "type": "bar_chart",
                "title": "Frecuencia de Términos",
                "path": path,
                "top_terms": sorted_kw[:10]
            }
        except ImportError:
            logger.warning("matplotlib no instalado, saltando visualización")
            return {"type": "bar_chart", "error": "matplotlib library not installed"}
        except Exception as e:
            logger.error(f"Error en bar_chart: {e}")
            return {"type": "bar_chart", "error": str(e)}
    
    def _create_network_graph(self, networks: List[Dict]) -> Dict[str, Any]:
        """Crea gráfico de red semántica"""
        try:
            import networkx as nx
            import matplotlib.pyplot as plt
            
            if not networks or not networks[0].get("edges"):
                return {"type": "network_graph", "error": "No network data provided"}
            
            G = nx.Graph()
            edges = networks[0]["edges"][:100]  # Limitar a 100 aristas
            
            for edge in edges:
                G.add_edge(edge["source"], edge["target"], weight=edge.get("weight", 1))
            
            fig, ax = plt.subplots(figsize=(12, 8))
            pos = nx.spring_layout(G, k=1, iterations=50, seed=42)
            
            # Tamaño de nodos por grado
            degrees = dict(G.degree())
            node_sizes = [300 + degrees.get(node, 1) * 100 for node in G.nodes()]
            
            nx.draw_networkx_edges(G, pos, alpha=0.3, ax=ax)
            nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="lightblue", ax=ax)
            nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)
            
            ax.set_title("Red Semántica de Co-ocurrencia")
            ax.axis("off")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.output_dir, f"network_{timestamp}")
            plt.tight_layout()
            plt.savefig(f"{path}.png", dpi=150)
            plt.savefig(f"{path}.svg")
            plt.close()
            
            return {
                "type": "network_graph",
                "title": "Red Semántica",
                "path": path,
                "node_count": G.number_of_nodes(),
                "edge_count": G.number_of_edges()
            }
        except ImportError:
            logger.warning("networkx no instalado, saltando visualización")
            return {"type": "network_graph", "error": "networkx library not installed"}
        except Exception as e:
            logger.error(f"Error en network_graph: {e}")
            return {"type": "network_graph", "error": str(e)}
    
    def _create_timeline(self, temporal: Dict[str, Any]) -> Dict[str, Any]:
        """Crea línea de tiempo de publicaciones"""
        try:
            import matplotlib.pyplot as plt
            
            pub_per_year = temporal.get("publications_per_year", {})
            if not pub_per_year:
                return {"type": "timeline", "error": "No temporal data provided"}
            
            years = sorted(pub_per_year.keys())
            counts = [pub_per_year[y] for y in years]
            
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(years, counts, marker="o", linewidth=2, markersize=6, color="darkgreen")
            ax.fill_between(years, counts, alpha=0.2, color="green")
            ax.set_xlabel("Año")
            ax.set_ylabel("Número de Publicaciones")
            ax.set_title("Evolución Temporal de Publicaciones")
            ax.grid(alpha=0.3)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.output_dir, f"timeline_{timestamp}")
            plt.tight_layout()
            plt.savefig(f"{path}.png", dpi=150)
            plt.savefig(f"{path}.svg")
            plt.close()
            
            return {
                "type": "timeline",
                "title": "Evolución Temporal",
                "path": path,
                "year_range": f"{min(years)}-{max(years)}",
                "total_publications": sum(counts)
            }
        except ImportError:
            logger.warning("matplotlib no instalado, saltando visualización")
            return {"type": "timeline", "error": "matplotlib library not installed"}
        except Exception as e:
            logger.error(f"Error en timeline: {e}")
            return {"type": "timeline", "error": str(e)}
    
    def _create_cluster_map(self, clusters: List[Dict]) -> Dict[str, Any]:
        """Crea mapa de clusters temáticos"""
        try:
            import matplotlib.pyplot as plt
            
            if not clusters:
                return {"type": "cluster_map", "error": "No cluster data provided"}
            
            themes = [c["theme"] for c in clusters[:10]]
            counts = [c["doc_count"] for c in clusters[:10]]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            colors = plt.cm.Set3(range(len(themes)))
            wedges, texts, autotexts = ax.pie(counts, labels=themes, autopct="%1.1f%%", 
                                              colors=colors, startangle=90)
            ax.set_title("Distribución de Clusters Temáticos")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.output_dir, f"clusters_{timestamp}")
            plt.tight_layout()
            plt.savefig(f"{path}.png", dpi=150)
            plt.savefig(f"{path}.svg")
            plt.close()
            
            return {
                "type": "cluster_map",
                "title": "Clusters Temáticos",
                "path": path,
                "cluster_count": len(clusters)
            }
        except ImportError:
            logger.warning("matplotlib no instalado, saltando visualización")
            return {"type": "cluster_map", "error": "matplotlib library not installed"}
        except Exception as e:
            logger.error(f"Error en cluster_map: {e}")
            return {"type": "cluster_map", "error": str(e)}
    
    def _create_triangulation_matrix(self, synthesis: Dict[str, Any]) -> Dict[str, Any]:
        """Crea visualización de matriz de triangulación"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            matrix_data = synthesis.get("triangulation", {})
            by_type = matrix_data.get("by_source_type", {})
            
            if not by_type:
                return {"type": "triangulation_matrix", "error": "No triangulation data"}
            
            labels = list(by_type.keys())
            values = list(by_type.values())
            
            fig, ax = plt.subplots(figsize=(8, 6))
            bars = ax.bar(labels, values, color="teal")
            ax.set_ylabel("Cantidad de Fuentes")
            ax.set_title("Triangulación por Tipo de Fuente")
            ax.tick_params(axis="x", rotation=45)
            
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       str(val), ha="center", va="bottom")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.output_dir, f"triangulation_{timestamp}")
            plt.tight_layout()
            plt.savefig(f"{path}.png", dpi=150)
            plt.savefig(f"{path}.svg")
            plt.close()
            
            return {
                "type": "triangulation_matrix",
                "title": "Matriz de Triangulación",
                "path": path,
                "data": by_type
            }
        except ImportError:
            logger.warning("matplotlib no instalado, saltando visualización")
            return {"type": "triangulation_matrix", "error": "matplotlib library not installed"}
        except Exception as e:
            logger.error(f"Error en triangulation_matrix: {e}")
            return {"type": "triangulation_matrix", "error": str(e)}
    
    def _create_summary_dashboard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea dashboard resumen"""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.gridspec import GridSpec
            
            fig = plt.figure(figsize=(12, 8))
            gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)
            
            # Panel 1: Keywords
            ax1 = fig.add_subplot(gs[0, 0])
            keywords = data.get("keywords", {})
            if keywords:
                top_kw = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:8]
                terms = [k for k, v in top_kw]
                vals = [v for k, v in top_kw]
                ax1.barh(terms[::-1], vals[::-1], color="steelblue")
                ax1.set_title("Términos Principales")
            
            # Panel 2: Clusters
            ax2 = fig.add_subplot(gs[0, 1])
            clusters = data.get("clusters", [])
            if clusters:
                themes = [c["theme"] for c in clusters[:6]]
                counts = [c["doc_count"] for c in clusters[:6]]
                ax2.bar(themes, counts, color="darkgreen")
                ax2.set_title("Clusters")
                ax2.tick_params(axis="x", rotation=45)
            
            # Panel 3: Temporal
            ax3 = fig.add_subplot(gs[1, 0])
            temporal = data.get("temporal", {}).get("publications_per_year", {})
            if temporal:
                years = sorted(temporal.keys())
                counts = [temporal[y] for y in years]
                ax3.plot(years, counts, marker="o", color="darkred")
                ax3.set_title("Evolución Temporal")
                ax3.tick_params(axis="x", rotation=45)
            
            # Panel 4: Info
            ax4 = fig.add_subplot(gs[1, 1])
            ax4.axis("off")
            info_text = "Resumen del Análisis\n\n"
            if keywords:
                info_text += f"Términos únicos: {len(keywords)}\n"
            if clusters:
                info_text += f"Clusters: {len(clusters)}\n"
            if temporal:
                info_text += f"Años cubiertos: {len(temporal)}\n"
            ax4.text(0.1, 0.5, info_text, fontsize=12, verticalalignment="center",
                    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
            
            fig.suptitle("Dashboard de Análisis - KAI-Ethno", fontsize=14, fontweight="bold")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.output_dir, f"dashboard_{timestamp}")
            plt.savefig(f"{path}.png", dpi=150)
            plt.savefig(f"{path}.svg")
            plt.close()
            
            return {
                "type": "summary_dashboard",
                "title": "Dashboard Resumen",
                "path": path
            }
        except ImportError:
            logger.warning("matplotlib no instalado, saltando visualización")
            return {"type": "summary_dashboard", "error": "matplotlib library not installed"}
        except Exception as e:
            logger.error(f"Error en dashboard: {e}")
            return {"type": "summary_dashboard", "error": str(e)}
    
    async def create_semantic_network(self, network_data: Dict) -> str:
        """Crea visualización de red semántica"""
        result = self._create_network_graph([network_data])
        return result.get("path", "")
    
    async def create_ant_map(self, actor_data: Dict) -> str:
        """Crea mapa de Actor-Red"""
        # Mapeo similar a red semántica pero con metadatos de actantes
        result = self._create_network_graph([actor_data])
        return result.get("path", "")
