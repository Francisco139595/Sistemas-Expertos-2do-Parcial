# Motor de Inferencia · Sistemas Expertos 7E262

Del lenguaje natural al árbol semántico. Página web estática (HTML + CSS + JavaScript, sin dependencias).

## Archivos
- `index.html` – estructura de la página
- `estilos.css` – diseño
- `motor.js` – parser de español → átomos → fórmulas, y el árbol semántico (reglas α/β, cierre de ramas, modelos)
- `app.js` – interfaz: tablas, dibujo del árbol en SVG, botones de paso a paso

## Abrir y correr dentro de Visual Studio Code
1. Descomprime el ZIP. En VS Code: **Archivo → Abrir carpeta…** → `motor-inferencia`.
2. VS Code te sugerirá instalar la extensión recomendada **Live Preview** (de Microsoft). Acepta.
   (O búscala en Extensiones: `ms-vscode.live-server`.)
3. Abre `index.html` y pulsa el ícono de vista previa (arriba a la derecha, una lupa con una pantalla),
   o clic derecho en `index.html` → **Show Preview**.
4. Se abre una **pestaña dentro de VS Code** con la interfaz funcionando. Al editar y guardar
   `motor.js`, `app.js` o `estilos.css`, la pestaña se actualiza sola.

Sin instalar nada: `Ctrl+Shift+P` → **Simple Browser: Show** sirve para ver una URL
(por ejemplo la de GitHub Pages) dentro de VS Code.

## Publicar con URL pública (GitHub Pages)
1. Crea un repositorio público en GitHub, por ejemplo `motor-inferencia`.
2. En VS Code: pestaña **Control de código fuente** → *Publicar en GitHub* (o sube los 4 archivos desde la web de GitHub con *Add file → Upload files*).
3. En GitHub: **Settings → Pages → Branch: main / (root) → Save**.
4. En 1–2 minutos queda en `https://TU-USUARIO.github.io/motor-inferencia/` — esa es la URL que se entrega.

Alternativa rápida: arrastra la carpeta a https://app.netlify.com/drop.

## Caso de prueba
```
Si es de día, entonces voy a trabajar.
Si llueve, entonces no voy a trabajar.
Es de día.
```
Resultado esperado: R1: p → q, R2: r → ¬q, R3: p · 2 ramas cerradas, 1 abierta · modelo p = V, q = V, r = F.
