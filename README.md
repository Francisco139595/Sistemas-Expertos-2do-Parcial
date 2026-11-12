# Motor de Inferencia (Python) · Sistemas Expertos 7E262

Del lenguaje natural al árbol semántico. Escribe reglas en español; el programa saca los átomos,
traduce los conectores a fórmulas, construye el árbol semántico paso a paso y lista los modelos.

## Archivos
- `motor.py` – toda la lógica: parser de español, átomos, fórmulas, árbol semántico (α/β), cierre de ramas y modelos.
- `almacen.py` – persistencia: guarda cada base de conocimiento como .txt en la carpeta `bases/`.
- `voz.py` – interfaz de voz (VUI): Whisper para oír, F5/E2-TTS o edge-tts para hablar.
- `voz_config.json` – ajustes de voz (modelo de Whisper, voz, F5/E2-TTS).
- `app.py` – interfaz gráfica con Streamlit (tablas, árbol dibujado, explicación, voz, resultados).
- `requirements.txt` – dependencias (streamlit y las librerías de voz).
- `.streamlit/config.toml` – tema oscuro.
- `.vscode/launch.json` – para correr con F5 desde VS Code.

## Correr en VS Code
1. Abre la carpeta en VS Code (**Archivo → Abrir carpeta…**).
2. Abre una terminal (**Terminal → New Terminal**) y ejecuta:
   ```
   py -3.12 -m pip install -r requirements.txt
   ```
3. Ejecuta:
   ```
   py -3.12 -m streamlit run app.py
   ```
   (o presiona **F5** y elige «Motor de inferencia (Streamlit)»).
4. Se abre en `http://localhost:8501`. Para verlo dentro de VS Code:
   `Ctrl+Shift+P` → **Simple Browser: Show** → `http://localhost:8501`.

Probar solo la lógica en consola: `py -3.12 motor.py`

## Componentes (tercer parcial)
- **Dominio de conocimiento**: primera línea de comentario del .txt; se muestra en su recuadro.
- **Base de conocimiento**: las reglas y hechos (carpeta `bases/`), más los descubrimientos.
- **Motor de inferencia**: árbol semántico, DPLL, encadenamiento hacia adelante y hacia atrás (con preguntas tipo Akinator).
- **VUI**: grabas la pista con el micrófono, Whisper la transcribe, y al final el programa dice la respuesta en voz alta.
- **Motor de explicación**: «¿por qué se descarta / confirma hN?» muestra la cadena de reglas que lleva a la contradicción.
- **Modelo de lenguaje**: Whisper (voz → texto), F5/E2-TTS o edge-tts (texto → voz) y el intérprete que acomoda la pista a las frases de la base.

## Preguntas tipo Akinator
- **Hacia adelante**: el programa pregunta características (sí / no / no sé) y con cada respuesta descarta hipótesis hasta llegar a una.
  Escoge la pregunta que mejor parte a las hipótesis que quedan.
- **Hacia atrás**: escoges una hipótesis (la meta); el programa busca la regla que la concluye y pregunta solo las premisas
  que no puede deducir, hasta demostrarla o descartarla.
- Las hipótesis son los renglones `# h1: …`; si no hay, se usan las conclusiones finales de las reglas («… entonces es X»).
- **Mundo cerrado**: lo que concluyen las reglas solo es cierto si se cumple alguna de esas reglas. Se activa solo en bases
  de personajes; en bases de examen (con `# h1:`) va apagado.
- Para dar de alta personajes: recuadro de reglas → «agregar personaje o concepto». Se guarda como
  `Si … y … entonces es <nombre>`.
- Se puede contestar con la voz: «sí», «no» o «no sé».

## Voz
- La voz se elige en el recuadro de voz (se guarda en `voz_config.json`). Las voces «multilingüe» son las más naturales.
- Si dice «voz de Windows (robótica)», la voz neural no funcionó: revisa el internet o corre `py -3.12 -m pip install -U edge-tts`.
- La primera vez que se usa el micrófono, Whisper descarga su modelo (`small`, unos 460 MB). Si va lento, cambia a `base` o `tiny` en `voz_config.json`.
- Si Whisper no está, usa Google (necesita internet).
- Para hablar usa edge-tts (necesita internet); sin internet usa la voz de Windows.
- F5-TTS / E2-TTS: `py -3.12 -m pip install f5-tts`, pon `"f5_usar": true`, un .wav de 5 a 15 s con la voz a imitar en `f5_audio_referencia` y lo que dice ese audio en `f5_texto_referencia`. Necesita tarjeta NVIDIA para ir rápido.

## URL pública (Streamlit Community Cloud, gratis)
1. Sube esta carpeta a un repositorio público de GitHub.
2. Entra a https://share.streamlit.io con tu cuenta de GitHub → **Create app**.
3. Elige el repositorio, rama `main` y archivo `app.py` → **Deploy**.
4. Te da una URL tipo `https://tu-app.streamlit.app` — esa es la que se entrega.
