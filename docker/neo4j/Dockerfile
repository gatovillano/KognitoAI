FROM neo4j:5.15-community

# Instalar APOC de forma estática
RUN wget -O /var/lib/neo4j/plugins/apoc-5.15.0-core.jar \
    https://github.com/neo4j/apoc/releases/download/5.15.0/apoc-5.15.0-core.jar

# Configurar permisos
RUN chown neo4j:neo4j /var/lib/neo4j/plugins/apoc-5.15.0-core.jar

# Configuración personalizada
COPY neo4j.conf /var/lib/neo4j/conf/neo4j.conf

# Script de inicialización
COPY init-neo4j.sh /docker-entrypoint-initdb.d/
RUN chmod +x /docker-entrypoint-initdb.d/init-neo4j.sh

EXPOSE 7474 7687
