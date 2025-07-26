from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ========= CONFIGURACIÓN INICIAL =========

# Cargar y preparar datos turísticos
try:
    df = pd.read_csv("rnt_limpio.csv")
    # Normalización de datos basada en los valores únicos proporcionados
    df['MUNICIPIO'] = df['MUNICIPIO'].str.strip().str.upper()
    df['CATEGORIA'] = df['CATEGORIA'].str.strip().str.upper()
    
    # Corrección de categorías según los datos mostrados
    categoria_correcciones = {
        'ESTABLECIMIENTOS DE ALOJAMIENTO TURÍSTICO': 'ESTABLECIMIENTOS DE ALOJAMIENTO TURISTICO',
        'OFICINAS DE REPRESENTACION TURÍSTICA': 'OFICINAS DE REPRESENTACION TURISTICA',
        'VIVIENDAS TURÍSTICAS': 'VIVIENDAS TURISTICAS',
        'ESTABLECIMIENTOS DE GASTRONOMÍA': 'ESTABLECIMIENTOS DE GASTRONOMIA',
        'ARRENDADORES DE VEHÍCULOS PARA TURISMO NACIONAL E INTERNACIONAL': 'ARRENDADORES DE VEHICULOS PARA TURISMO NACIONAL E INTERNACIONAL'
    }
    df['CATEGORIA'] = df['CATEGORIA'].replace(categoria_correcciones)
    
    print("✅ Datos cargados correctamente")
    print(f"Municipios únicos: {len(df['MUNICIPIO'].unique())}")
    print(f"Categorías únicas: {len(df['CATEGORIA'].unique())}")
except Exception as e:
    print(f"❌ Error cargando CSV: {str(e)}")
    df = pd.DataFrame()

# Conexión a PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://usuario:contraseña@servidor/bd")

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ Conexión a PostgreSQL exitosa")
except Exception as e:
    print(f"❌ Error conectando a PostgreSQL: {str(e)}")
    conn = None

# Crear tablas necesarias
if conn:
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS respuestas_formulario (
                    id SERIAL PRIMARY KEY,
                    viajas_con VARCHAR(50),
                    interes_viaje VARCHAR(50),
                    duracion_viaje VARCHAR(100),
                    clima_preferencia VARCHAR(100),
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS busquedas (
                    id SERIAL PRIMARY KEY,
                    termino_busqueda VARCHAR(100),
                    municipio VARCHAR(100),
                    categoria VARCHAR(100),
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
    except Exception as e:
        print(f"❌ Error creando tablas: {str(e)}")

# ========= ENDPOINTS PRINCIPALES =========

@app.route("/")
def index():
    return {
        "status": "active",
        "version": "1.3.0",
        "municipios_disponibles": len(df['MUNICIPIO'].unique()),
        "categorias_disponibles": len(df['CATEGORIA'].unique()),
        "documentacion": "https://github.com/JUANPABLO-0826/TravelInsight"
    }

# ========= CONSULTAS DE DATOS =========

@app.route("/api/municipios")
def municipios():
    """Obtiene lista de todos los municipios disponibles"""
    try:
        municipios = sorted(df['MUNICIPIO'].dropna().unique().tolist())
        return jsonify(municipios)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/categorias")
def categorias():
    """Obtiene lista de todas las categorías disponibles"""
    try:
        categorias = sorted(df['CATEGORIA'].dropna().unique().tolist())
        return jsonify(categorias)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/destinos")
def destinos():
    """Obtiene los primeros 10 destinos"""
    try:
        return jsonify(df.head(10).to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========= FILTRADOS ESPECÍFICOS =========

@app.route("/api/destinos/<municipio>")
def destinos_por_municipio(municipio):
    """Filtra destinos por municipio (ej: TUNJA, CHIA)"""
    try:
        filtro = df[df['MUNICIPIO'].str.lower() == municipio.lower()]
        if filtro.empty:
            return jsonify({"mensaje": f"No se encontraron destinos en {municipio}"}), 404
        return jsonify(filtro.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/categoria/<categoria>")
def por_categoria(categoria):
    """Filtra destinos por categoría (ej: BARES, PARQUES TEMÁTICOS)"""
    try:
        # Normalizar categoría para coincidir con los datos
        categoria = categoria.upper()
        if 'TURÍSTIC' in categoria:
            categoria = categoria.replace('TURÍSTIC', 'TURISTIC')
            
        filtro = df[df['CATEGORIA'] == categoria]
        if filtro.empty:
            return jsonify({"mensaje": f"No se encontraron destinos de categoría {categoria}"}), 404
        return jsonify(filtro.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filtrar")
def filtrar_combinado():
    """Filtrado combinado municipio + categoría con paginación"""
    try:
        municipio = request.args.get("municipio", "").upper()
        categoria = request.args.get("categoria", "").upper()
        pagina = int(request.args.get("pagina", 1))
        por_pagina = int(request.args.get("por_pagina", 10))

        # Registrar búsqueda
        if conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO busquedas (municipio, categoria)
                    VALUES (%s, %s)
                """, (municipio if municipio else None, categoria if categoria else None))
                conn.commit()

        # Aplicar filtros
        filtro = df.copy()
        if municipio:
            filtro = filtro[filtro['MUNICIPIO'] == municipio]
        if categoria:
            if 'TURÍSTIC' in categoria:
                categoria = categoria.replace('TURÍSTIC', 'TURISTIC')
            filtro = filtro[filtro['CATEGORIA'] == categoria]

        # Paginación
        total = len(filtro)
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        resultados = filtro[inicio:fin].to_dict(orient="records")

        return jsonify({
            "resultados": resultados,
            "paginacion": {
                "pagina": pagina,
                "por_pagina": por_pagina,
                "total": total,
                "paginas": (total + por_pagina - 1) // por_pagina
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========= BÚSQUEDA Y RECOMENDACIONES =========

@app.route("/api/buscar")
def buscar_destinos():
    """Búsqueda textual en nombres y descripciones"""
    try:
        termino = request.args.get("q", "").lower()
        if not termino:
            return jsonify([])
            
        resultados = df[
            df['NOMBRE'].str.lower().str.contains(termino) |
            df['DESCRIPCION'].str.lower().str.contains(termino)
        ].to_dict(orient="records")

        # Registrar búsqueda
        if conn and termino:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO busquedas (termino_busqueda)
                    VALUES (%s)
                """, (termino,))
                conn.commit()

        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recomendaciones")
def generar_recomendaciones():
    """Sistema de recomendaciones basado en intereses"""
    try:
        interes = request.args.get("interes", "").upper()
        municipio = request.args.get("municipio", "").upper()
        
        if not interes:
            return jsonify({"error": "Parámetro 'interes' requerido"}), 400
        
        # Normalizar categoría de interés
        if 'TURÍSTIC' in interes:
            interes = interes.replace('TURÍSTIC', 'TURISTIC')
        
        # Filtrado inicial
        recomendaciones = df.copy()
        if interes:
            recomendaciones = recomendaciones[recomendaciones['CATEGORIA'].str.contains(interes)]
        if municipio:
            recomendaciones = recomendaciones[recomendaciones['MUNICIPIO'] == municipio]
        
        # Si no hay resultados, devolver aleatorios del municipio o generales
        if len(recomendaciones) == 0:
            if municipio:
                recomendaciones = df[df['MUNICIPIO'] == municipio].sample(min(5, len(df)))
            else:
                recomendaciones = df.sample(min(5, len(df)))
        
        return jsonify({
            "recomendaciones": recomendaciones.to_dict(orient="records"),
            "total": len(recomendaciones)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========= FORMULARIO Y PREFERENCIAS =========

@app.route("/api/formulario", methods=["POST"])
def guardar_formulario():
    """Guarda las preferencias del usuario"""
    try:
        data = request.get_json()
        required = ["viajas_con", "interes_viaje", "duracion_viaje", "clima_preferencia"]
        
        if not all(field in data for field in required):
            return jsonify({"error": "Faltan campos requeridos"}), 400
        
        if conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO respuestas_formulario 
                    (viajas_con, interes_viaje, duracion_viaje, clima_preferencia)
                    VALUES (%s, %s, %s, %s)
                """, (
                    data["viajas_con"],
                    data["interes_viaje"],
                    data["duracion_viaje"],
                    data["clima_preferencia"]
                ))
                conn.commit()
        
        return jsonify({"mensaje": "Preferencias guardadas exitosamente"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========= ESTADÍSTICAS =========

@app.route("/api/estadisticas")
def obtener_estadisticas():
    """Devuelve estadísticas basadas en los datos turísticos"""
    try:
        # Top 5 municipios con más destinos
        top_municipios = df['MUNICIPIO'].value_counts().head(5).to_dict()
        
        # Top 5 categorías más comunes
        top_categorias = df['CATEGORIA'].value_counts().head(5).to_dict()
        
        return jsonify({
            "total_destinos": len(df),
            "total_municipios": len(df['MUNICIPIO'].unique()),
            "total_categorias": len(df['CATEGORIA'].unique()),
            "top_municipios": top_municipios,
            "top_categorias": top_categorias,
            "ejemplo_municipios": ["TUNJA", "PAIPA", "SOGAMOSO", "CHIA", "VILLA DE LEYVA"],
            "ejemplo_categorias": ["BARES", "PARQUES TEMÁTICOS", "ESTABLECIMIENTOS DE ALOJAMIENTO TURISTICO", "GUIAS DE TURISMO", "AGENCIAS DE VIAJES"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
