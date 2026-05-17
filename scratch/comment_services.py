# comment_services.py
import re

file_path = "/home/gato/Proyectos/KognitoAI/kognito-ai/docker-compose.yml"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# We want to comment out the services: core, telegram_client, frontend, and telegram_panel.
# Let's locate the start of 'core:' and comment out lines up to before '# 6. Base de Datos de Grafos (Neo4j)'

pattern = r"(  # 2. El Cerebro \(Servicio Core API\)\n(?:.*\n)*?  telegram_panel:(?:\n|.)*?host-gateway\")"
# Wait, let's be more precise by reading lines and commenting them out by index.
lines = content.splitlines(keepends=True)

# Find line indexes for core and the end of telegram_panel
start_idx = None
end_idx = None

for idx, line in enumerate(lines):
    if "# 2. El Cerebro (Servicio Core API)" in line:
        start_idx = idx
    if "telegram_panel:" in line:
        # End index will be when we reach neo4j database or next section
        for j in range(idx, len(lines)):
            if "# 6. Base de Datos de Grafos (Neo4j)" in lines[j]:
                end_idx = j
                break
        if end_idx:
            break

if start_idx is not None and end_idx is not None:
    print(f"Commenting from line {start_idx + 1} to {end_idx}")
    
    comment_header = [
        "  # =========================================================================\n",
        "  # [HOST MODE ACTIVE]\n",
        "  # Los servicios core, frontend, telegram_client y telegram_panel\n",
        "  # se ejecutan localmente en el host para optimizar el rendimiento y \n",
        "  # facilitar el desarrollo directo.\n",
        "  # Para usarlos en Docker en el futuro, descomenta las siguientes secciones.\n",
        "  # =========================================================================\n\n"
    ]
    
    commented_lines = []
    for idx in range(start_idx, end_idx):
        line = lines[idx]
        # Comment out if not already commented out
        if line.strip() and not line.strip().startswith("#"):
            # Preserve leading spaces and prefix with #
            leading_spaces = len(line) - len(line.lstrip())
            commented_line = line[:leading_spaces] + "# " + line[leading_spaces:]
            commented_lines.append(commented_line)
        else:
            commented_lines.append(line)
            
    # Reassemble lines
    new_lines = lines[:start_idx] + comment_header + commented_lines + lines[end_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("".join(new_lines))
    print("Successfully commented out host services in docker-compose.yml!")
else:
    print(f"Error finding start or end indices: start={start_idx}, end={end_idx}")
