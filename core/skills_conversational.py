#!/usr/bin/env python3
"""
🗣️ Agent Skills - Interfaz Conversacional en Lenguaje Natural
Permite al agente entender y usar skills diciendo cosas como:
  - "necesito buscar información sobre..."
  - "muéstrame skills disponibles"
  - "quiero hacer un análisis RAG de esto"
"""

import json
from pathlib import Path
from typing import Optional
import re


class SkillsConversationalInterface:
    """Interfaz conversacional para skills en lenguaje natural"""

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = Path(skills_dir)
        self.load_skills_catalog()

    def load_skills_catalog(self):
        """Carga el catálogo de skills disponibles"""
        registry_file = Path(".skills-registry.json")
        if registry_file.exists():
            with open(registry_file) as f:
                self.registry = json.load(f)
        else:
            self.registry = {"skills": []}

        # Catálogo de skills conocidos con palabras clave
        self.skills_catalog = {
            "search-and-research": {
                "name": "Búsqueda y Investigación",
                "keywords": ["buscar", "investigación", "web", "tavily", "duckduckgo", "scraping", "información", "contenido"],
                "description": "Búsqueda avanzada en internet, análisis de contenido web",
                "ejemplos": [
                    "busca información sobre {tema}",
                    "necesito investigar {query}",
                    "extrae contenido de {url}",
                    "haz una búsqueda de {términos}",
                ],
                "use_case": "Cuando necesites encontrar, buscar o analizar información en internet"
            },
            "retrieval-augmented-generation": {
                "name": "Análisis RAG",
                "keywords": ["rag", "análisis", "recuperación", "knowledge graph", "neo4j", "memoria", "contexto"],
                "description": "Recuperación y análisis de información con contexto", 
                "ejemplos": [
                    "analiza esto con RAG",
                    "dame análisis detallado de {tema}",
                    "busca relaciones entre {conceptos}",
                    "haz un análisis profundo de {documento}",
                ],
                "use_case": "Cuando necesites análisis profundo con contexto histórico"
            },
            "knowledge-memory-management": {
                "name": "Gestión de Conocimiento",
                "keywords": ["memoria", "conocimiento", "guardar", "recordar", "relaciones", "grafo", "contexto"],
                "description": "Gestión de memoria y relaciones de conocimiento",
                "ejemplos": [
                    "recuerda esto para más tarde",
                    "guarda esto en memoria",
                    "crea una relación entre {A} y {B}",
                    "actualiza mi conocimiento sobre {tema}",
                ],
                "use_case": "Cuando quieras que el agente recuerde y relacione información"
            },
        }

    def parse_user_intent(self, user_message: str) -> dict:
        """
        Analiza la intención del usuario y detecta qué skill es más relevante.
        
        Retorna: {
            "intent": "search" | "analyze" | "remember" | "unknown",
            "skill": nombre del skill más relevante,
            "confidence": 0.0-1.0,
            "action": descripción de lo que debería hacer,
            "parameters": parámetros extraídos,
        }
        """
        
        message_lower = user_message.lower()
        
        # Buscar matches de keywords
        matches = {}
        for skill_id, skill_info in self.skills_catalog.items():
            score = 0
            found_keywords = []
            for keyword in skill_info["keywords"]:
                if keyword in message_lower:
                    score += 1
                    found_keywords.append(keyword)
            if score > 0:
                matches[skill_id] = {
                    "score": score,
                    "keywords": found_keywords,
                    "info": skill_info
                }
        
        if not matches:
            return {
                "intent": "unknown",
                "skill": None,
                "confidence": 0.0,
                "action": "No identifiqué qué skill usar. ¿Puedes ser más específico?",
                "parameters": {},
                "suggestion": self.get_skills_description()
            }
        
        # Seleccionar el mejor match
        best_match = max(matches.items(), key=lambda x: x[1]["score"])
        skill_id = best_match[0]
        skill_info = best_match[1]["info"]
        
        # Detectar parámetros
        parameters = self.extract_parameters(user_message)
        
        # Determinar intención
        if "search" in skill_id or "buscar" in message_lower:
            intent = "search"
        elif "rag" in skill_id or "análisis" in message_lower:
            intent = "analyze"
        elif "memory" in skill_id or "recuerda" in message_lower or "guardar" in message_lower:
            intent = "remember"
        else:
            intent = "unknown"
        
        # Confidence basada en relevancia
        confidence = min(1.0, best_match[1]["score"] / 3)
        
        # Generar acción
        action = self.generate_action(skill_id, user_message, parameters)
        
        return {
            "intent": intent,
            "skill": skill_id,
            "skill_name": skill_info["name"],
            "confidence": confidence,
            "action": action,
            "parameters": parameters,
            "keywords_found": best_match[1]["keywords"],
        }

    def extract_parameters(self, message: str) -> dict:
        """Extrae parámetros de la intención del usuario"""
        params = {}
        
        # Buscar queries con "sobre", "de", "acerca"
        patterns = [
            (r"(?:sobre|de|acerca de)\s+(.+?)(?:\?|$|\.)", "topic"),
            (r"(?:busca?|investiga?|analiza?)\s+(.+?)(?:\?|$|\.)", "query"),
            (r"(?:en|desde)\s+(.+?)(?:\?|$|\.)", "source"),
        ]
        
        for pattern, key in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                params[key] = match.group(1).strip()
        
        return params

    def generate_action(self, skill_id: str, message: str, params: dict) -> str:
        """Genera una descripción clara de la acción a tomar"""
        skill = self.skills_catalog[skill_id]
        
        action_templates = {
            "search-and-research": "Voy a buscar información en internet {topic} y te traeré los resultados más relevantes",
            "retrieval-augmented-generation": "Voy a analizar {query} usando el contexto y la memoria disponible",
            "knowledge-memory-management": "Voy a guardar y relacionar esta información en tu base de conocimiento",
        }
        
        template = action_templates.get(skill_id, f"Usando {skill['name']}")
        
        # Reemplazar placeholders
        if params.get("topic"):
            template = template.format(topic=f"sobre {params['topic']}")
        elif params.get("query"):
            template = template.format(query=params["query"])
        else:
            # Extraer del mensaje
            if "{" in template:
                template = template.split("{")[0].strip()
        
        return template

    def get_skills_description(self) -> str:
        """Retorna una descripción de skills disponibles"""
        skills_text = "📚 Skills disponibles:\n\n"
        for skill_id, skill in self.skills_catalog.items():
            skills_text += f"• **{skill['name']}**: {skill['use_case']}\n"
            skills_text += f"  Palabras clave: {', '.join(skill['keywords'][:5])}\n\n"
        return skills_text

    def respond_conversationally(self, user_message: str) -> str:
        """Responde al usuario de forma conversacional"""
        intent_data = self.parse_user_intent(user_message)
        
        if intent_data["intent"] == "unknown":
            return f"""❓ No estoy seguro qué hacer con eso.

{intent_data['suggestion']}

💡 Intenta algo como:
- "Busca información sobre inteligencia artificial"
- "Haz un análisis profundo sobre este tema"
- "Guarda esto en mi memoria"
"""
        
        confidence_emoji = "✅" if intent_data["confidence"] >= 0.7 else "⚠️"
        
        response = f"""{confidence_emoji} Entendí que quieres:
{intent_data['action']}

🎯 Usaré el skill: **{intent_data['skill_name']}**
Confianza: {int(intent_data['confidence']*100)}%
"""
        
        if intent_data["parameters"]:
            response += f"\n📝 Parámetros extraídos:\n"
            for key, value in intent_data["parameters"].items():
                response += f"  • {key}: {value}\n"
        
        response += f"""
¿Continúo con esta acción? (Sí/No/Modifica)
"""
        return response

    def get_agent_system_prompt(self) -> str:
        """Retorna un system prompt mejorado para el agente"""
        
        skills_desc = ""
        for skill_id, skill in self.skills_catalog.items():
            skills_desc += f"""
### {skill['name']} ({skill_id})
Descripción: {skill['description']}
Cuándo usar: {skill['use_case']}
Palabras clave: {', '.join(skill['keywords'])}

Ejemplos de solicitudes del usuario:
{chr(10).join('- ' + ex for ex in skill['ejemplos'])}
"""
        
        return f"""# Sistema de Skills para Agentes Inteligentes

Eres un asistente inteligente con acceso a múltiples skills especializados.
Cuando el usuario pida algo, identifica qué skill es más relevante.

## Skills Disponibles

{skills_desc}

## Instrucciones

1. **Escucha con atención**: Analiza lo que el usuario pide en lenguaje natural
2. **Identifica el skill**: Determina qué skill es más relevante para la tarea
3. **Confirma tu entendimiento**: Di qué vas a hacer de forma clara
4. **Ejecuta**: Usa el skill apropiado
5. **Entrega resultados**: Presenta los resultados de forma clara y útil

## Ejemplos de Conversación

**Usuario**: "Necesito investigar sobre tendencias de IA"
**Agente**: "Voy a hacer una búsqueda avanzada sobre tendencias de IA y te traeré los articulos más relevantes recientes."

**Usuario**: "Guarda que la IA está revolucionando la medicina"
**Agente**: "He guardado esto en tu base de conocimiento y lo he relacionado con conceptos de IA y medicina."

**Usuario**: "Analiza el impacto de la IA en negocios"
**Agente**: "Voy a hacer un análisis profundo usando el contexto disponible sobre IA y negocios, conectando con información que ya tenemos."

## Reglas Importantes

- Usa lenguaje natural y conversacional
- Si no entiendes, pide aclaraciones
- Siempre explica qué skill vas a usar y por qué
- Presenta resultados de forma clara y estructurada
- Si un skill puede ayudar, úsalo sin que el usuario tenga que pedirlo explícitamente
"""


# Ejemplo de uso
if __name__ == "__main__":
    import sys
    
    interface = SkillsConversationalInterface()
    
    # Ejemplos de conversación
    test_messages = [
        "Necesito buscar información sobre machine learning",
        "Haz un análisis profundo de la economía global",
        "Recuerda que visitamos la conferencia de IA en marzo",
        "Muéstrame skills disponibles",
        "Quiero algo relacionado con datos",
    ]
    
    print("🗣️ Skills Conversational Interface - Examples\n")
    print("=" * 60)
    
    for message in test_messages:
        print(f"\n👤 Usuario: {message}")
        print("-" * 60)
        response = interface.respond_conversationally(message)
        print(response)
        print("=" * 60)
    
    # Mostrar system prompt
    print("\n" + "=" * 60)
    print("📋 SYSTEM PROMPT PARA EL AGENTE:")
    print("=" * 60)
    print(interface.get_agent_system_prompt())
