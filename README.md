## ⚙️ Configuración Inicial

### 1. Configurar Submódulos

**Primera vez - Inicializar submódulos:**

```bash
git submodule update --init --recursive
```

**Actualizar referencias a los submódulos:**

```bash
git submodule update --remote
```

### 2. Turno de interacción (mai-core, contexto y acción)

El chat web y la voz pasan por mai-core. BLIP describe la escena; Milvus y Gemma (o OpenAI, si hay clave) responden; robótica habla y ejecuta el gesto.

```bash
cp .env.template .env
mkdir -p data/milvus
sudo docker compose build pmai-core
sudo docker compose up
```

`PMAI_CORE_PYTHONPATH` en `.env` debe quedar así (ya viene en la plantilla):

```bash
PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src
```

Antes del primer arranque:

- Si falta `pmai-model-vision-language/models/gguf/gemma-4-E2B-it-Q4_K_M.gguf`, mai-core lo descarga de Hugging Face al arrancar. Hace falta red esa primera vez.
- Opcional: `OPENAI_API_KEY` en `pmai-model-vision-language/.env`. Con red y clave se usa `gpt-4o-mini`; si no, Gemma.
- Opcional: descripciones de gestos en `/usr/src/app/data/action-descriptions.json` dentro de `pba-ms-robotics` (`ACTION_DESCRIPTIONS_PATH`). Si no existe, la descripción llega vacía y el modelo usa el nombre.
- Milvus Lite crea `conocimiento` e `interacciones` al arrancar mai-core. El archivo queda en `pmai-model-vision-language/utils/milvus/androide_milvus.db`.
- El primer inicio descarga BLIP y el modelo de embeddings, y carga Gemma. Tarda.

sudo docker compose up
Contraseña: 12345

Usuario:
admin-prometeo@unilibre.edu.co
Prometeo2026*


sudo ufw allow 3000/tcp
sudo ufw allow 3000/udp

sudo ufw allow 4200/tcp
sudo ufw allow 4200/udp

ip a
ip a

wlp2s0
10.211.14.115

Buscar pmas-web-main
Buscar src/enviroments/ud
Se debe cambiar la IP en gatewayUrl




# Para agregar preguntas u orcaciones
/home/rone/Documentos/r-one/pba-launcher/pmas-web-main/src/app/pages/robotics-chat/robotics-chat.ts

Se edita decirQuickOptions o chatQuickOptions

