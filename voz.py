# Para correr el programa: py -3.12 -m streamlit run app.py
# Interfaz de voz (VUI)
#   oír:   Whisper (faster-whisper, local) y si no está instalado, Google (necesita internet)
#   hablar: F5-TTS / E2-TTS (local, necesita voz de referencia) y si no, edge-tts (voz neural de
#           Microsoft, necesita internet) y si no, pyttsx3 (voz de Windows, sin internet)
import asyncio
import io
import json
import os
import tempfile

CARPETA = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(CARPETA, 'voz_config.json')

# valores por defecto; se pueden cambiar en voz_config.json
AJUSTES = {
    'whisper_modelo': 'small',          # tiny, base, small, medium, large-v3
    'whisper_dispositivo': 'auto',      # auto, cpu, cuda
    'voz_edge': 'es-MX-DaliaNeural',    # voz de edge-tts
    'velocidad': '-5%',                 # más lento o más rápido: '-10%', '+0%', '+10%'
    'f5_usar': False,                   # True para usar F5-TTS / E2-TTS
    'f5_modelo': {},                    # parámetros para F5TTS(...), por ejemplo {"model": "E2TTS_Base"}
    'f5_audio_referencia': '',          # .wav de 5 a 15 segundos con la voz que se va a imitar
    'f5_texto_referencia': '',          # lo que se dice en ese .wav
}
if os.path.exists(CONFIG):
    try:
        with open(CONFIG, encoding='utf-8') as f:
            AJUSTES.update(json.load(f))
    except (OSError, ValueError):
        pass

# voces neuronales de edge-tts que suenan naturales en español
VOCES = {
    'Dalia · mujer, México': 'es-MX-DaliaNeural',
    'Jorge · hombre, México': 'es-MX-JorgeNeural',
    'Paloma · mujer, EE. UU. (español)': 'es-US-PalomaNeural',
    'Alonso · hombre, EE. UU. (español)': 'es-US-AlonsoNeural',
    'Elvira · mujer, España': 'es-ES-ElviraNeural',
    'Álvaro · hombre, España': 'es-ES-AlvaroNeural',
    'Ava · multilingüe, muy natural (acento leve)': 'en-US-AvaMultilingualNeural',
    'Andrew · multilingüe, muy natural (acento leve)': 'en-US-AndrewMultilingualNeural',
}

_whisper = None
_f5 = None


def guardar_ajustes(**cambios):
    # guarda en voz_config.json para que se quede aunque se cierre el programa
    AJUSTES.update(cambios)
    try:
        with open(CONFIG, 'w', encoding='utf-8') as f:
            json.dump(AJUSTES, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _archivo_temporal(datos, ext):
    f = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    f.write(datos)
    f.close()
    return f.name


def transcribir(audio):
    # regresa (texto, con qué se transcribió, error)
    global _whisper
    errores = []
    try:
        from faster_whisper import WhisperModel
        if _whisper is None:
            dispositivo = AJUSTES['whisper_dispositivo']
            _whisper = WhisperModel(AJUSTES['whisper_modelo'], device=dispositivo,
                                    compute_type='int8' if dispositivo != 'cuda' else 'float16')
        ruta = _archivo_temporal(audio, '.wav')
        try:
            segmentos, _ = _whisper.transcribe(ruta, language='es', vad_filter=True)
            texto = ' '.join(s.text.strip() for s in segmentos).strip()
        finally:
            os.remove(ruta)
        return texto, f'Whisper ({AJUSTES["whisper_modelo"]})', None
    except ImportError:
        errores.append('Whisper no está instalado')
    except Exception as e:
        errores.append(f'Whisper falló: {e}')
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio)) as fuente:
            datos = r.record(fuente)
        return r.recognize_google(datos, language='es-MX'), 'Google', None
    except ImportError:
        errores.append('SpeechRecognition no está instalado')
    except Exception as e:
        errores.append(f'Google falló: {e}')
    return '', None, ' · '.join(errores)


def _hablar_f5(texto):
    global _f5
    if not AJUSTES['f5_usar'] or not AJUSTES['f5_audio_referencia']:
        return None
    from f5_tts.api import F5TTS
    if _f5 is None:
        _f5 = F5TTS(**AJUSTES['f5_modelo'])
    salida = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
    try:
        _f5.infer(ref_file=AJUSTES['f5_audio_referencia'], ref_text=AJUSTES['f5_texto_referencia'],
                  gen_text=texto, file_wave=salida)
        with open(salida, 'rb') as f:
            return f.read()
    finally:
        os.remove(salida)


def _hablar_edge(texto):
    import edge_tts
    salida = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
    try:
        com = edge_tts.Communicate(texto, AJUSTES['voz_edge'], rate=AJUSTES.get('velocidad', '+0%'))
        asyncio.run(com.save(salida))
        with open(salida, 'rb') as f:
            return f.read()
    finally:
        os.remove(salida)


def _hablar_pyttsx3(texto):
    import pyttsx3
    salida = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
    try:
        motor = pyttsx3.init()
        motor.setProperty('rate', 165)
        for v in motor.getProperty('voices'):
            if 'spanish' in (v.name or '').lower() or 'es' in str(getattr(v, 'languages', '')).lower():
                motor.setProperty('voice', v.id)
                break
        motor.save_to_file(texto, salida)
        motor.runAndWait()
        with open(salida, 'rb') as f:
            return f.read()
    finally:
        os.remove(salida)


_hechos = {}


def hablar(texto):
    # regresa (audio, tipo, con qué se generó, errores); audio None si nada funcionó
    # errores también trae por qué fallaron las voces anteriores (para saber por qué suena robótica)
    clave = (texto, AJUSTES['voz_edge'], AJUSTES.get('velocidad'), AJUSTES['f5_usar'])
    if clave in _hechos:
        return _hechos[clave]
    errores = []
    for nombre, funcion, tipo in (('F5-TTS', _hablar_f5, 'audio/wav'),
                                  ('edge-tts', _hablar_edge, 'audio/mp3'),
                                  ('voz de Windows', _hablar_pyttsx3, 'audio/wav')):
        try:
            audio = funcion(texto)
            if audio:
                _hechos[clave] = (audio, tipo, nombre, ' · '.join(errores) or None)
                return _hechos[clave]
        except ImportError:
            if nombre != 'F5-TTS':
                errores.append(f'{nombre} no está instalado')
        except Exception as e:
            errores.append(f'{nombre} falló: {e}')
    return None, None, None, ' · '.join(errores)
