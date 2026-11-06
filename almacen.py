# Para correr el programa: py -3.12 -m streamlit run app.py
# Persistencia: cada base de conocimiento se guarda como un archivo .txt en la carpeta "bases"
import os
import re
from datetime import datetime

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bases')
BORRADOR = os.path.join(CARPETA, '_borrador.txt')
ACTUAL = os.path.join(CARPETA, '_actual.txt')

os.makedirs(CARPETA, exist_ok=True)


def nombre_limpio(nombre):
    # quita la extensión y los caracteres que no se pueden usar en un nombre de archivo
    nombre = os.path.splitext(os.path.basename(nombre))[0]
    nombre = re.sub(r'[^\w\- áéíóúÁÉÍÓÚñÑ]', '', nombre).strip()
    return nombre or 'base'


def ruta(nombre):
    return os.path.join(CARPETA, nombre_limpio(nombre) + '.txt')


def listar():
    # nombres de todas las bases guardadas, en orden alfabético
    nombres = [os.path.splitext(f)[0] for f in os.listdir(CARPETA)
               if f.endswith('.txt') and not f.startswith('_')]
    return sorted(nombres, key=str.lower)


def leer(nombre):
    with open(ruta(nombre), encoding='utf-8') as f:
        return f.read()


def guardar(nombre, texto):
    with open(ruta(nombre), 'w', encoding='utf-8') as f:
        f.write(texto)
    return nombre_limpio(nombre)


def borrar(nombre):
    if os.path.exists(ruta(nombre)):
        os.remove(ruta(nombre))


def fecha(nombre):
    t = os.path.getmtime(ruta(nombre))
    return datetime.fromtimestamp(t).strftime('%d/%m/%Y %H:%M')


def decodificar(datos):
    # los archivos del Bloc de notas pueden venir en UTF-8 o en ANSI (latin-1)
    for cod in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            return datos.decode(cod)
        except UnicodeDecodeError:
            continue
    return datos.decode('utf-8', errors='ignore')


def leer_borrador():
    # lo último que se escribió en el cuadro de reglas
    if os.path.exists(BORRADOR):
        with open(BORRADOR, encoding='utf-8') as f:
            return f.read()
    return ''


def guardar_borrador(texto):
    with open(BORRADOR, 'w', encoding='utf-8') as f:
        f.write(texto)


def leer_actual():
    # nombre de la última base que se tenía abierta
    if os.path.exists(ACTUAL):
        with open(ACTUAL, encoding='utf-8') as f:
            return f.read().strip()
    return ''


def guardar_actual(nombre):
    with open(ACTUAL, 'w', encoding='utf-8') as f:
        f.write(nombre)
