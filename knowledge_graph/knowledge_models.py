# knowledge_graph/knowledge_models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class Node(BaseModel):
    """
    Modelo base para representar un nodo en el grafo de conocimiento.
    """
    label: str = Field(..., description="Etiqueta del nodo (e.g., Concepto, Persona, Lugar).")
    properties: Dict[str, Any] = Field(..., description="Diccionario de propiedades del nodo.")

class Concept(Node):
    """
    Modelo para representar un concepto en el grafo de conocimiento.
    """
    label: str = "Concepto"
    properties: Dict[str, Any] = Field(..., description="Diccionario de propiedades del concepto.")

class Persona(Node):
    """
    Modelo para representar una persona en el grafo de conocimiento.
    """
    label: str = "Persona"
    properties: Dict[str, Any] = Field(..., description="Diccionario de propiedades de la persona.")

class Lugar(Node):
    """
    Modelo para representar un lugar en el grafo de conocimiento.
    """
    label: str = "Lugar"
    properties: Dict[str, Any] = Field(..., description="Diccionario de propiedades del lugar.")

#  Puedes agregar más modelos para diferentes tipos de nodos

class Relationship(BaseModel):
    """
    Modelo para representar una relación entre dos nodos en el grafo de conocimiento.
    """
    type: str = Field(..., description="Tipo de relación (e.g., ES_UN, TIENE_UN, CAUSA).")
    start_node_label: str = Field(..., description="Etiqueta del nodo de inicio.")
    start_node_property_name: str = Field(..., description="Nombre de la propiedad para identificar el nodo de inicio.")
    start_node_property_value: Any = Field(..., description="Valor de la propiedad para identificar el nodo de inicio.")
    end_node_label: str = Field(..., description="Etiqueta del nodo de fin.")
    end_node_property_name: str = Field(..., description="Nombre de la propiedad para identificar el nodo de fin.")
    end_node_property_value: Any = Field(..., description="Valor de la propiedad para identificar el nodo de fin.")
    properties: Optional[Dict[str, Any]] = Field(None, description="Diccionario de propiedades de la relación (opcional).")

# Ejemplo de uso:
if __name__ == '__main__':
    # Crear un nodo Concepto
    concepto_data = {
        "nombre": "Inteligencia Artificial",
        "descripcion": "Campo de la informática dedicado a la creación de sistemas inteligentes."
    }
    concepto = Concept(properties=concepto_data)
    print(f"Concepto: {concepto.json(indent=2)}")

    # Crear un nodo Persona
    persona_data = {
        "nombre": "Alan Turing",
        "ocupacion": "Científico de la computación"
    }
    persona = Persona(properties=persona_data)
    print(f"Persona: {persona.json(indent=2)}")

    # Crear una relación
    relacion = Relationship(
        type="INSPIRADO_POR",
        start_node_label="Concepto",
        start_node_property_name="nombre",
        start_node_property_value="Inteligencia Artificial",
        end_node_label="Persona",
        end_node_property_name="nombre",
        end_node_property_value="Alan Turing"
    )
    print(f"Relación: {relacion.json(indent=2)}")