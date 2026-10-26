# Motor de Inferencia (Python) · Sistemas Expertos 7E262

Del lenguaje natural al árbol semántico. Escribe reglas en español; el programa saca los átomos,
traduce los conectores a fórmulas, construye el árbol semántico paso a paso y lista los modelos.

## Archivos
- `motor.py` – toda la lógica: parser de español, átomos, fórmulas, árbol semántico (α/β), cierre de ramas y modelos.
- `app.py` – interfaz gráfica con Streamlit (tablas, árbol dibujado, botones paso a paso, resultados).
- `requirements.txt` – dependencias (solo `streamlit`).
- `.streamlit/config.toml` – tema oscuro.
- `.vscode/launch.json` – para correr con F5 desde VS Code.

## Correr en VS Code
1. Abre la carpeta en VS Code (**Archivo → Abrir carpeta…**).
2. Abre una terminal (**Terminal → New Terminal**) y ejecuta:
   ```
   pip install -r requirements.txt
   ```
3. Ejecuta:
   ```
   streamlit run app.py
   ```
   (o presiona **F5** y elige «Motor de inferencia (Streamlit)»).
4. Se abre en `http://localhost:8501`. Para verlo dentro de VS Code:
   `Ctrl+Shift+P` → **Simple Browser: Show** → `http://localhost:8501`.

Probar solo la lógica en consola: `python motor.py`

## URL pública (Streamlit Community Cloud, gratis)
1. Sube esta carpeta a un repositorio público de GitHub.
2. Entra a https://share.streamlit.io con tu cuenta de GitHub → **Create app**.
3. Elige el repositorio, rama `main` y archivo `app.py` → **Deploy**.
4. Te da una URL tipo `https://tu-app.streamlit.app` — esa es la que se entrega.
