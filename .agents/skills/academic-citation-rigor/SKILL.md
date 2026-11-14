---
name: academic-citation-rigor
description: Protocolo de rigor y verificación bibliográfica científica (APA 7). Uso obligatorio para redactar textos académicos, papers, tesinas, revisiones bibliográficas o verificar fuentes contra bases de datos indexadas (Crossref, OpenAlex, PubMed).
tags:
  - academic
  - citations
  - research
  - crossref
  - openalex
  - pubmed
  - apa7
---

# Procedimiento Operativo Estándar: Rigor y Verificación Bibliográfica (APA 7)

Este protocolo es de **cumplimiento estricto e innegociable** para cualquier redacción científica, elaboración de marcos teóricos, revisiones del estado del arte, tesinas de investigación o respuestas donde se citen fuentes y autores.

---

## 1. El Principio Fundamental: Cero Memoria Paramétrica

Los Modelos de Lenguaje (LLMs) son generadores probabilísticos; **nunca recuerdan con precisión determinista números de volumen, páginas, iniciales de autores ni revistas**. Cuando intentan generar una bibliografía de memoria, asocian autores con revistas plausibles (ej. inventar que un paper fue publicado en *The Lancet* o *Gaceta Sanitaria*) y conjeturan números de página o nombres.

### 🚨 Mandato de Integridad:
* **Queda terminantemente prohibido generar o reconstruir metadatos bibliográficos de memoria.**
* Todo título, lista de coautores, nombre de revista, volumen, número, página y enlace DOI **debe provenir obligatoriamente de una consulta a la herramienta `academic_citation_verifier`** o del texto explícito de un documento RAG adjunto.
* Si un estudio es conocido conceptualmente pero no se encuentra en las bases de datos oficiales, **JAMÁS se debe adivinar la revista ni los coautores**. Debe registrarse explícitamente:
  `[Referencia no verificada en registros indexados: Autor, Año, Tema]`
  o citarse como referencia secundaria.

---

## 2. Herramienta de Búsqueda y Verificación: `academic_citation_verifier`

La herramienta `academic_citation_verifier` consulta en tiempo real **Crossref**, **OpenAlex** y **PubMed**. Debe ser ejecutada antes de asentar cualquier afirmación con cita formal.

### Modos de Operación:

1. **Modo `verify` (Contrastar y validar un paper conocido):**
   * **Cuándo usar:** Cuando tienes el apellido del autor y el tema o título aproximado.
   * **Ejemplo:**
     ```json
     {
       "query": "Carvalho Gámez Valdés Chemsex conductas sexuales",
       "mode": "verify"
     }
     ```
   * **Salida esperada:** La cita APA 7 oficial, la revista real (*Health and Addictions/Salud y Drogas*), volumen, páginas y DOI oficial.

2. **Modo `search` (Búsqueda temática de literatura científica):**
   * **Cuándo usar:** Al construir un marco teórico o responder con evidencia reciente sobre un tema.
   * **Ejemplo:**
     ```json
     {
       "query": "prejuicio sexual salud mental minorias chile",
       "mode": "search",
       "source": "all"
     }
     ```

3. **Modo `doi` (Resolución determinista por DOI):**
   * **Cuándo usar:** Cuando el texto o documento original contiene un DOI y se requiere la ficha bibliográfica oficial completa.
   * **Ejemplo:**
     ```json
     {
       "query": "10.21134/haaj.v20i1.495",
       "mode": "doi"
     }
     ```

---

## 3. Protocolo de Verificación en 4 Pasos

```
┌─────────────────────────┐
│ 1. Extracción de Claims  │ Identifica afirmaciones y autores que sustentan el texto.
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 2. Consulta en Registro  │ Invoca `academic_citation_verifier` con los datos clave.
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 3. Contraste de 4 Ejes   │ Valida: 1) Título, 2) Revista, 3) Coautores completos, 4) DOI.
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 4. Ensamblaje APA 7     │ Inserta la cita en el texto y la ficha en la bibliografía.
└─────────────────────────┘
```

### Reglas para los 4 Ejes de Contraste:
1. **Autores completos e iniciales:** No omitir coautores. En APA 7 se incluyen hasta 20 autores antes de usar puntos suspensivos (`...`). Las iniciales deben ser exactas (ej. *Moreno-Gámez, L.* y no *P.*).
2. **Nombre oficial de la revista:** No traducir nombres de revistas (si es *Behavioral Sciences*, no poner *Ciencias de la Conducta* ni inventar *Adicciones*).
3. **Numeración y paginación:** Solo incluir volumen, número y rango de páginas si están presentes en la respuesta de la API.
4. **DOI activo:** Siempre que esté disponible, debe consignarse en formato URL (`https://doi.org/...`).

---

## 4. Tratamiento de Fuentes Secundarias, Tesis e Informes Técnicos

Cuando una obra citada no es un artículo de revista con DOI:
* **Tesis de grado o posgrado:** Identificar la institución académica correspondiente.
  * *Ejemplo correcto:* Blanco Ospina, S., Corredor, E., & Marimón Gil, D. A. (2020). *Influencias discursivas y construcción de identidad sexual en personas LGBT* [Tesis de pregrado, Pontificia Universidad Javeriana]. Repositorio Institucional ODUCAL.
  * *Error a evitar:* Asignar una tesis a una revista científica ficticia.
* **Informes técnicos gubernamentales o de ONGs:** Indicar el organismo emisor.
  * *Ejemplo correcto:* Curto, J., Dolengevich, H., Soriano, R., & Belza, M. J. (2020). *Documento técnico: Abordaje de la salud mental del usuario con prácticas de chemsex*. Ministerio de Sanidad de España.
* **Citas Secundarias (*as cited in*):** Si un dato se conoce porque fue leído dentro de otro paper (ej. citado en González & Morales, 2024), y no se ha podido validar el documento primario original:
  * En el texto: `(Carvalho et al., 2020, como se citó en González Rodríguez & Morales Yáñez, 2024)`.
  * En la bibliografía: Consignar la referencia de González Rodríguez & Morales Yáñez (2024), que es la fuente que realmente se consultó.

---

## 5. Checklist de Auto-Auditoría antes de Entregar Cualquier Texto

Antes de responder al usuario con un texto que incluya citas:

- [ ] ¿He ejecutado `academic_citation_verifier` para cada una de las referencias citadas?
- [ ] ¿Todos los apellidos e iniciales coinciden con los devueltos por Crossref / OpenAlex / PubMed?
- [ ] ¿He verificado que ninguna revista fue inventada o asignada por proximidad temática?
- [ ] ¿Cada referencia en la bibliografía cuenta con su DOI (`https://doi.org/...`) o URL de repositorio verificable?
- [ ] Si alguna fuente no pudo ser confirmada, ¿se ha advertido claramente al usuario en lugar de intentar aparentar certeza?
