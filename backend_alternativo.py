"""
Backend Flask alternativo - Usa subprocess para llamar a SWI-Prolog
NO requiere PySwip (evita problemas de configuración)
Ejecutar: python backend_alternativo.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import tempfile
import os
import shutil
import sys
import locale

app = Flask(__name__)
CORS(app)

# Ruta al archivo Prolog
PROLOG_FILE = "asistente_finanzas.pl"

def verificar_swipl():
    """Verifica que swipl esté disponible"""
    env_cmd = os.environ.get('SWIPL_CMD') or os.environ.get('SWI_PROLOG')
    cmd = env_cmd or 'swipl'

    # Limpiar posibles comillas y expandir variables de entorno
    if env_cmd:
        env_cmd = env_cmd.strip().strip('"').strip("'")
        env_cmd = os.path.expandvars(env_cmd)
        # Reasignar cmd limpio
        cmd = env_cmd or cmd

    # On Windows, try swipl.exe if plain name not found
    candidates = [cmd]
    if sys.platform.startswith('win') and not cmd.lower().endswith('.exe'):
        candidates.append(cmd + '.exe')

    for c in candidates:
        # If path given, check file exists; otherwise use which
        if os.path.isabs(c) or os.path.sep in c:
            if os.path.exists(c) and os.access(c, os.X_OK):
                return True
        else:
            if shutil.which(c):
                return True

    # Try common executable names as last resort
    if shutil.which('swipl') or shutil.which('swipl.exe'):
        return True

    return False

def get_swipl_cmd():
    """Devuelve la manera correcta de invocar SWI-Prolog como lista (para subprocess).
    Permite configurar la ruta con la variable de entorno `SWIPL_CMD`.
    """
    env_cmd = os.environ.get('SWIPL_CMD') or os.environ.get('SWI_PROLOG')
    if env_cmd:
        env_cmd = env_cmd.strip().strip('"').strip("'")
        env_cmd = os.path.expandvars(env_cmd)
        # Si la ruta existe, devolverla
        if os.path.exists(env_cmd):
            return env_cmd
        # Si no existe como ruta, devolver lo que haya (permite nombres como 'swipl')
        return env_cmd

    # Prefer the system executable found by shutil.which
    sw = shutil.which('swipl') or shutil.which('swipl.exe')
    if sw:
        return sw

    # En Windows, intentar rutas de instalación comunes
    if sys.platform.startswith('win'):
        common_paths = [
            r"C:\Program Files\swipl\bin\swipl.exe",
            r"C:\Program Files (x86)\swipl\bin\swipl.exe",
            r"C:\Program Files\swipl\swipl.exe",
        ]
        for p in common_paths:
            if os.path.exists(p) and os.access(p, os.X_OK):
                print(f"SWI-Prolog encontrado en ruta estándar: {p}")
                return p

    # Fallback to 'swipl' (will likely fail but caller handles it)
    return 'swipl'

def crear_consulta_prolog(perfil_dict):
    """Crea un archivo temporal con la consulta Prolog"""
    
    # Convertir valores Python a formato Prolog
    def to_prolog_value(v):
        if isinstance(v, bool):
            return 'true' if v else 'false'
        elif isinstance(v, str):
            return f"'{v}'"
        elif isinstance(v, list):
            if not v:
                return '[]'
            return '[' + ','.join([f"meta('{m['tipo']}',{m['meses']})" for m in v]) + ']'
        else:
            return str(v)
    
    # Construir el dict de Prolog
    campos = []
    for key, value in perfil_dict.items():
        prolog_value = to_prolog_value(value)
        campos.append(f"{key}: {prolog_value}")
    
    perfil_prolog = "_{ " + ", ".join(campos) + " }"
    
    # Crear archivo temporal con la consulta
    consulta = f"""
:- consult('{PROLOG_FILE}').

ejecutar_consulta :-
    Perfil = {perfil_prolog},
    recomendaciones(Perfil, Recs),
    maplist(writeln, Recs),
    halt.

:- ejecutar_consulta.
"""
    
    return consulta

def ejecutar_prolog(consulta_texto):
    """Ejecuta una consulta Prolog y retorna los resultados"""
    
    # Crear archivo temporal para la consulta
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pl', delete=False, encoding='utf-8') as f:
        f.write(consulta_texto)
        temp_file = f.name
    
    try:
        # Ejecutar SWI-Prolog usando el ejecutable detectado o configurado
        swipl_cmd = get_swipl_cmd()
        cmd = [swipl_cmd, '-q', '-t', 'halt', temp_file] if os.path.isabs(swipl_cmd) or os.path.sep in swipl_cmd or shutil.which(swipl_cmd) else [swipl_cmd, '-q', '-t', 'halt', temp_file]

        # Ejecutar y capturar bytes para evitar errores de decodificación en la lectura
        # Mostrar el comando que se va a ejecutar para depuración
        try:
            print(f"Ejecutando comando Prolog: {cmd}")
        except Exception:
            pass

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
            timeout=15
        )

        # Decodificar usando la codificación preferida del sistema, reemplazando bytes inválidos
        enc = locale.getpreferredencoding(False) or 'utf-8'
        stdout_bytes = result.stdout or b''
        stderr_bytes = result.stderr or b''
        try:
            stdout_text = stdout_bytes.decode(enc, errors='replace')
        except Exception:
            stdout_text = stdout_bytes.decode('utf-8', errors='replace')
        try:
            stderr_text = stderr_bytes.decode(enc, errors='replace')
        except Exception:
            stderr_text = stderr_bytes.decode('utf-8', errors='replace')

        # Procesar salida
        if result.returncode == 0:
            recomendaciones = [line.strip() for line in stdout_text.split('\n') if line.strip()]
            return recomendaciones
        else:
            print(f"Error en Prolog (exit {result.returncode}): {stderr_text}")
            return []
            
    except subprocess.TimeoutExpired:
        print("Timeout ejecutando Prolog")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(temp_file)
        except:
            pass

def categorizar_recomendaciones(recomendaciones):
    """Categoriza las recomendaciones según palabras clave"""
    
    categorias = {
        'ahorro': [],
        'presupuesto': [],
        'deuda': [],
        'metas': [],
        'seguro': [],
        'educacion': [],
        'general': []
    }
    
    for rec in recomendaciones:
        rec_lower = rec.lower()
        
        # Categorizar por palabras clave
        if any(word in rec_lower for word in ['ahorro', 'fondo de emergencia', 'tasa de ahorro']):
            category = 'ahorro'
            priority = 'high' if any(w in rec_lower for w in ['crea', 'incrementa']) else 'medium'
        elif any(word in rec_lower for word in ['gasto', 'presupuesto', 'vivienda', 'alimentación', 'transporte', 'registra']):
            category = 'presupuesto'
            priority = 'high' if 'superan' in rec_lower else 'medium'
        elif any(word in rec_lower for word in ['deuda', 'interés', 'apr', 'tarjeta', 'crédito', 'mínimo']):
            category = 'deuda'
            priority = 'high' if any(w in rec_lower for w in ['sobreendeudamiento', 'apr alta']) else 'medium'
        elif any(word in rec_lower for word in ['meta', 'jubilación', 'smart']):
            category = 'metas'
            priority = 'medium'
        elif any(word in rec_lower for word in ['seguro', 'testamento', 'protección']):
            category = 'seguro'
            priority = 'high' if 'no cuentas' in rec_lower else 'medium'
        elif any(word in rec_lower for word in ['nivel', 'conocimiento', 'curso', 'simulador', 'portafolio']):
            category = 'educacion'
            priority = 'low'
        else:
            category = 'general'
            priority = 'low'
        
        categorias[category].append({
            'text': rec,
            'priority': priority
        })
    
    return categorias

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica que el servidor esté funcionando"""
    swipl_ok = verificar_swipl()
    prolog_file_ok = os.path.exists(PROLOG_FILE)
    swipl_path = os.environ.get('SWIPL_CMD') or shutil.which('swipl') or shutil.which('swipl.exe')
    
    return jsonify({
        'status': 'ok' if swipl_ok and prolog_file_ok else 'error',
        'message': 'Servidor Flask funcionando correctamente',
        'swipl_disponible': swipl_ok,
        'archivo_prolog_encontrado': prolog_file_ok,
        'swipl_path_detectado': swipl_path
    })

@app.route('/api/recomendaciones', methods=['POST'])
def get_recomendaciones():
    """Obtiene recomendaciones financieras"""
    
    try:
        # Obtener datos del request
        data = request.json
        print(f"Datos recibidos: {json.dumps(data, indent=2)}")
        
        # Validar datos requeridos
        required_fields = [
            'ingreso', 'gasto_total', 'ahorro_mensual', 'meses_fondo',
            'vivienda', 'alimentacion', 'transporte', 'deudas_total',
            'tasa_interes_apr', 'gasto_medico_ratio'
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f'Campo requerido faltante: {field}'
                }), 400
        
        # Crear consulta Prolog
        consulta = crear_consulta_prolog(data)
        print("Ejecutando consulta Prolog...")
        
        # Ejecutar Prolog
        recomendaciones = ejecutar_prolog(consulta)
        print(f"✓ Se obtuvieron {len(recomendaciones)} recomendaciones")
        
        # Categorizar
        categorized = categorizar_recomendaciones(recomendaciones)
        
        return jsonify({
            'success': True,
            'total': len(recomendaciones),
            'recomendaciones': recomendaciones,
            'categorizadas': categorized
        })
        
    except Exception as e:
        print(f"✗ Error en endpoint: {e}")
        return jsonify({
            'error': f'Error procesando solicitud: {str(e)}'
        }), 500

@app.route('/api/ejemplo', methods=['GET'])
def get_ejemplo():
    """Obtiene un perfil de ejemplo"""
    
    ejemplo = {
        'ingreso': 15000,
        'gasto_total': 16500,
        'ahorro_mensual': 800,
        'meses_fondo': 0.5,
        'vivienda': 6000,
        'alimentacion': 5800,
        'transporte': 3500,
        'deudas_total': 5200,
        'cc_pago_minimo': True,
        'tasa_interes_apr': 42.0,
        'jubilacion_definida': False,
        'nivel_conocimiento': 'basic',
        'tiene_seguro_salud': False,
        'tiene_seguro_vida': False,
        'dependientes': True,
        'posee_auto': True,
        'tiene_seguro_auto': False,
        'gasto_medico_ratio': 0.18,
        'tiene_testamento': False,
        'registra_gastos': False,
        'metas': []
    }
    
    return jsonify({
        'success': True,
        'perfil': ejemplo
    })

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Iniciando servidor Flask (Versión Alternativa)")
    print("=" * 50)
    
    # Verificar requisitos
    swipl_ok = verificar_swipl()
    detected = get_swipl_cmd()
    if not swipl_ok:
        print("⚠️  ADVERTENCIA: No se encuentra SWI-Prolog")
        print("   Asegúrate de que 'swipl' esté en el PATH o configura la variable de entorno SWIPL_CMD")
    else:
        print("✓ SWI-Prolog encontrado")

    # Mostrar la ruta/valor detectado para diagnóstico
    try:
        print(f"SWI-Prolog detectado (get_swipl_cmd): {detected}")
    except Exception:
        pass
    
    if not os.path.exists(PROLOG_FILE):
        print(f"⚠️  ADVERTENCIA: No se encuentra {PROLOG_FILE}")
        print(f"   Asegúrate de que el archivo esté en: {os.path.abspath('.')}")
    else:
        print(f"✓ Archivo Prolog encontrado: {PROLOG_FILE}")
    
    print("\nEndpoints disponibles:")
    print("  GET  /api/health          - Verificar estado del servidor")
    print("  POST /api/recomendaciones - Obtener recomendaciones")
    print("  GET  /api/ejemplo         - Obtener perfil de ejemplo")
    print("=" * 50)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)