"""
Backend Flask para conectar la interfaz web con el motor Prolog
Autor: Sistema Experto de Finanzas
Requiere: Flask, Flask-CORS, pyswip
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import shutil
try:
    from pyswip import Prolog
    PROLOG_AVAILABLE = True
except Exception as e:
    Prolog = None
    PROLOG_AVAILABLE = False
    print(f"⚠️  pyswip no está disponible: {e}")
    print("   Si quieres usar `backend.py`, instala pyswip y SWI-Prolog o usa `backend_alternativo.py`")
import json

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde el frontend

# Inicializar Prolog solo si pyswip está disponible
prolog = None
if PROLOG_AVAILABLE:
    try:
        prolog = Prolog()
        # Intentar cargar el módulo de finanzas
        try:
            prolog.consult("asistente_finanzas.pl")
            print("✓ Módulo asistente_finanzas.pl cargado correctamente")
        except Exception as e:
            print(f"✗ Error al cargar el módulo Prolog: {e}")
    except Exception as e:
        print(f"✗ Error inicializando pyswip/Prolog: {e}")
        prolog = None
        PROLOG_AVAILABLE = False
        print("   Comprueba que SWI-Prolog esté instalado y que `swipl` esté en el PATH o configure la variable de entorno SWIPL_CMD.")
else:
    print("⚠️  pyswip no disponible: backend en modo degradado. Usa backend_alternativo.py si no puedes instalar pyswip/SWI-Prolog.")

def dict_to_prolog_dict(data):
    """
    Convierte un diccionario Python a formato de dict Prolog
    """
    # Convertir booleanos a átomos Prolog
    def convert_value(v):
        if isinstance(v, bool):
            return 'true' if v else 'false'
        elif isinstance(v, str):
            return f"'{v}'" if v else "''"
        elif isinstance(v, list):
            if not v:
                return '[]'
            # Convertir lista de metas
            metas_str = ','.join([f"meta('{m['tipo']}',{m['meses']})" for m in v])
            return f"[{metas_str}]"
        else:
            return str(v)
    
    # Construir el dict de Prolog
    fields = []
    for key, value in data.items():
        prolog_value = convert_value(value)
        fields.append(f"{key}: {prolog_value}")
    
    return f"_{{ {', '.join(fields)} }}"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    # Detectar si swipl está disponible en el sistema
    swipl_found = bool(os.environ.get('SWIPL_CMD') or shutil.which('swipl') or shutil.which('swipl.exe'))
    prolog_ok = prolog is not None
    status = 'ok' if prolog_ok else 'warning'
    message = 'Servidor Flask funcionando correctamente' if prolog_ok else 'Servidor Flask disponible, pero Prolog no está listo'
    return jsonify({
        'status': status,
        'message': message,
        'pyswip_installed': PROLOG_AVAILABLE,
        'swipl_detectado': swipl_found
    })

@app.route('/api/recomendaciones', methods=['POST'])
def get_recomendaciones():
    """
    Endpoint principal para obtener recomendaciones financieras
    Recibe un perfil financiero y devuelve recomendaciones
    """
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
        
        # Construir el perfil en formato Prolog dict
        perfil_dict = dict_to_prolog_dict(data)
        print(f"Dict Prolog generado: {perfil_dict}")
        
        # Construir la consulta Prolog
        query = f"recomendaciones({perfil_dict}, Recs)"
        print(f"Ejecutando query: {query}")
        
        # Ejecutar consulta
        recomendaciones = []
        try:
            result = list(prolog.query(query))
            if result:
                # Extraer las recomendaciones
                recs_list = result[0]['Recs']
                recomendaciones = recs_list
                print(f"✓ Se obtuvieron {len(recomendaciones)} recomendaciones")
        except Exception as e:
            print(f"Error en query Prolog: {e}")
            return jsonify({
                'error': f'Error ejecutando Prolog: {str(e)}'
            }), 500
        
        # Categorizar recomendaciones
        categorized = categorize_recommendations(recomendaciones)
        
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

def categorize_recommendations(recomendaciones):
    """
    Categoriza las recomendaciones según palabras clave
    """
    categories = {
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
            priority = 'high' if 'crea' in rec_lower or 'incrementa' in rec_lower else 'medium'
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
        
        categories[category].append({
            'text': rec,
            'priority': priority
        })
    
    return categories

@app.route('/api/ejemplo', methods=['GET'])
def get_ejemplo():
    """
    Endpoint para obtener un perfil de ejemplo
    """
    try:
        query = "ejemplo_perfil(Perfil)"
        result = list(prolog.query(query))
        
        if result:
            perfil = result[0]['Perfil']
            return jsonify({
                'success': True,
                'perfil': perfil
            })
        else:
            return jsonify({
                'error': 'No se pudo obtener el perfil de ejemplo'
            }), 404
            
    except Exception as e:
        return jsonify({
            'error': f'Error obteniendo ejemplo: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Iniciando servidor Flask")
    print("=" * 50)
    print("Endpoints disponibles:")
    print("  GET  /api/health          - Verificar estado del servidor")
    print("  POST /api/recomendaciones - Obtener recomendaciones")
    print("  GET  /api/ejemplo         - Obtener perfil de ejemplo")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)