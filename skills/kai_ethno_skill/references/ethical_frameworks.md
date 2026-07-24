# Marcos Éticos de Referencia

## Principios Fundamentales

### 1. Consentimiento Informado
- **Definición**: Acuerdo voluntario y continuo del participante
- **Requisitos**:
  - Información clara sobre fines, métodos, riesgos
  - Comprensión verificada del participante
  - Derecho a retirarse en cualquier momento
  - Documentación escrita cuando sea posible

### 2. Confidencialidad y Anonimato
- **Confidencialidad**: Protección de datos identificables
- **Anonimato**: Imposibilidad de identificación
- **Técnicas**:
  - Pseudonimización
  - Agregación de datos
  - Ofuscación de detalles identificativos

### 3. No Maleficencia
- **Principio**: No causar daño
- **Aplicación**:
  - Evaluación de riesgos físicos y psicológicos
  - Protección de poblaciones vulnerables
  - Evitar estigmatización

### 4. Justicia y Equidad
- **Selección justa de participantes**
- **Distribución equitativa de beneficios/costos**
- **Accesibilidad de resultados**

## Marcos Normativos Internacionales

### Declaración Universal de Derechos Humanos (1948)
- Art. 12: Derecho a la privacidad
- Art. 27: Derecho a participar en la vida cultural

### Convenio de Oviedo (1997)
- Consentimiento libre e informado
- Protección de personas con capacidad limitada

### GDPR (Reglamento UE 2016/679)
- Licitud, fairness, transparencia
- Minimización de datos
- Derecho al olvido
- Evaluación de Impacto (DPIA)

### APA Ethics Code (2017)
- Estándares de investigación con seres humanos
- Estándares de investigación con animales
- Estándares de publicación

### AAA Statement on Ethics (2012)
- "Do no harm" como principio rector
- Consulta con comunidades
- Transparencia metodológica

## Marcos Específicos por Tipo de Investigación

### Etnografía Digital
- **Netnografía (Kozinets, 2015)**:
  - Autenticidad de participantes online
  - Contextualización de interacciones digitales
  - Protección en espacios públicos/privados digitales
  
- **Investigación en Redes Sociales**:
  - Términos de servicio de plataformas
  - Expectativas de privacidad de usuarios
  - Cita de handles vs. nombres reales

### Etnografía Colaborativa
- **Investigación Participativa (PAR)**:
  - Co-diseño con comunidad
  - Beneficio mutuo
  - Propiedad compartida de resultados

### Investigación con Poblaciones Vulnerables
- **Menores de edad**: Consentimiento parental + asentimiento
- **Pueblos indígenas**: Consentimiento tribal + consulta comunitaria
- **Personas con discapacidad**: Accesibilidad de información

## Protocolos de Evaluación Ética

### Checklist de Evaluación
```
□ ¿Los participantes han dado consentimiento informado?
□ ¿Se protegen datos personales identificables?
□ ¿Existen riesgos físicos/psicológicos evaluados?
□ ¿La muestra es representativa y justa?
□ ¿La metodología es transparente?
□ ¿Se consultó con la comunidad estudiada?
□ ¿Los beneficios superan los riesgos?
□ ¿Hay plan de retiro de datos?
```

### Matriz de Riesgos
| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Identificación | Media | Alto | Anonimización |
| Malentendido cultural | Media | Medio | Consulta tribal |
| Sensibilidad temática | Alta | Alto | Revisión comunitaria |

## Veto Ético (Ethics Council Protocol)

### Derecho a Veto
Cualquier miembro del Ethics Council puede bloquear una investigación si:
1. Falta consentimiento documentado
2. Existe riesgo inminente de daño
3. Se violan derechos humanos fundamentales
4. La metodología es intrínsecamente dañina

### Proceso de Veto
1. **Bloqueo inmediato**: El agente detiene el flujo
2. **Notificación**: Se informa al usuario investigador
3. **Revisión**: El Consejo evalúa en 24h
4. **Resolución**: Aprobación condicional o rechazo definitivo

### Ejemplo de Bloqueo Ético
```python
class EthicalBlock(Exception):
    def __init__(self, evaluator, reason, severity):
        self.evaluator = evaluator
        self.reason = reason
        self.severity = severity  # "warning", "block", "critical"
        super().__init__(f"[{evaluator}] {reason}")
```

## Referencias Normativas

1. American Psychological Association. (2017). *Ethical Principles of Psychologists and Code of Conduct*.
2. American Anthropological Association. (2012). *Principles of Professional Responsibility*.
3. European Parliament. (2016). *General Data Protection Regulation (GDPR)*.
4. Council of Europe. (1997). *Convention for the Protection of Human Rights and Dignity of the Human Being*.
5. Kozinets, R. V. (2015). *Netnography: Redefined*. Sage.
