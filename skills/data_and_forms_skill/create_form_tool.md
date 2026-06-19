# Create Form Tool
Esta herramienta permite al agente crear formularios dinámicos. Los formularios pueden contener secciones y diversos tipos de campos como texto, áreas de texto, casillas de verificación, selectores y botones de radio.

## Uso
El agente debe proporcionar un nombre para el formulario y una lista de elementos (campos o secciones). 

### Ejemplo de Estructura de Elementos
```json
[
  {
    "title": "Información de Contacto",
    "description": "Por favor, introduce tus datos.",
    "elements": [
      {
        "label": "Nombre Completo",
        "type": "text",
        "is_required": true
      },
      {
        "label": "Correo Electrónico",
        "type": "text",
        "is_required": true
      }
    ]
  },
  {
    "label": "¿Cómo nos conociste?",
    "type": "select",
    "options": ["Redes Sociales", "Amigos", "Publicidad", "Otro"]
  }
]
```
