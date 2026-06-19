# Bases de Datos Académicas

## Antropología y Ciencias Sociales

### Bases de Datos Principales

#### AnthroSource
- **URL**: https://www.anthrosource.org/
- **Cobertura**: Artículos de Anthropological Association
- **Acceso**: Suscripción institucional
- **API**: No oficial (scraping con respeto robots.txt)

#### JSTOR Anthropology Collection
- **URL**: https://www.jstor.org/
- **Cobertura**: Revistas académicas de antropología
- **Acceso**: Suscripción
- **API**: No disponible públicamente

#### PubMed Central
- **URL**: https://pubmed.ncbi.nlm.nih.gov/
- **Cobertura**: Medicina y antropología médica
- **Acceso**: Abierto
- **API**: E-utilities (https://www.ncbi.nlm.nih.gov/books/NBK25501/)

#### Scopus
- **URL**: https://www.scopus.com/
- **Cobertura**: Multidisciplinario
- **Acceso**: Suscripción institucional
- **API**: Scopus API (requiere token)

#### Web of Science
- **URL**: https://www.webofscience.com/
- **Cobertura**: Multidisciplinario
- **Acceso**: Suscripción
- **API**: WoS API

### Repositorios de Acceso Abierto

#### Directory of Open Access Journals (DOAJ)
- **URL**: https://doaj.org/
- **Cobertura**: Revistas de acceso abierto
- **API**: https://doaj.org/api/v1/docs

#### arXiv
- **URL**: https://arxiv.org/
- **Cobertura**: Preprints de ciencias exactas y sociales
- **API**: arXiv API

#### Semantic Scholar
- **URL**: https://www.semanticscholar.org/
- **Cobertura**: Papers CS y ciencias sociales
- **API**: https://api.semanticscholar.org/

#### OpenAlex
- **URL**: https://openalex.org/
- **Cobertura**: Catálogo global de papers
- **API**: https://docs.openalex.org/

### Bases de Datos Especializadas

#### eHRAF World Cultures
- **URL**: https://ehrafworldcultures.yale.edu/
- **Cobertura**: Etnografías de todo el mundo
- **Acceso**: Suscripción
- **API**: No disponible

#### Human Relations Area Files
- **URL**: https://hraf.yale.edu/
- **Cobertura**: Datos etnográficos
- **Acceso**: Suscripción

#### ASFA (Aquatic Sciences and Fisheries Abstracts)
- **URL**: https://www.fao.org/asfa/en/
- **Cobertura**: Antropología marina y pesquera
- **Acceso**: Abierto

### Motores de Búsqueda Académica

#### Google Scholar
- **URL**: https://scholar.google.com/
- **Cobertura**: Amplia pero no exhaustiva
- **API**: No oficial (serpapi, scholarly)
- **Nota**: Respetar términos de servicio

#### Microsoft Academic
- **URL**: https://academic.microsoft.com/
- **Cobertura**: Multidisciplinario
- **API**: Descontinuada (2021)

#### BASE (Bielefeld Academic Search Engine)
- **URL**: https://www.base-search.net/
- **Cobertura**: Repositorios institucionales
- **API**: OAI-PMH

### Estrategias de Búsqueda

#### Búsqueda Boolean
```
("digital ethnography" OR "virtual ethnography" OR "online ethnography")
AND ("social media" OR "digital communities")
AND (2020:2024[Publication Date])
```

#### Búsqueda por Autor
```
AU:(hine_s OR pink_s OR boellstorff_t)
```

#### Búsqueda por Afiliación
```
AF:"University of California"
```

#### Búsqueda por Palabras Clave
```
TI("participant observation" AND "digital")
AB("netnography" OR "cyberethnography")
```

### Configuración de APIs

#### PubMed E-utilities
```python
import requests

base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
params = {
    "db": "pubmed",
    "term": "digital ethnography[Title/Abstract]",
    "retmax": 100,
    "retmode": "json",
    "api_key": "YOUR_API_KEY"
}
response = requests.get(f"{base_url}esearch.fcgi", params=params)
```

#### Semantic Scholar API
```python
import requests

headers = {"x-api-key": "YOUR_API_KEY"}
params = {
    "query": "digital ethnography",
    "fields": "title,authors,year,venue,citationCount",
    "limit": 100
}
response = requests.get(
    "https://api.semanticscholar.org/graph/v1/paper/search",
    headers=headers,
    params=params
)
```

### Consideraciones Éticas

- Respetar robots.txt de todos los sitios
- No exceder límites de rate de APIs
- Atribuir correctamente fuentes
- Considerar términos de servicio de cada plataforma
- Usar APIs oficiales cuando estén disponibles
