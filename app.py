from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# Carga tu CSV
df = pd.read_csv("rnt_limpio.csv")

# Conexión a Postgres (usa la URL de Render como variable de entorno o hardcodeada)
DATABASE_URL = os.environ.get("DATABASE_URL", 
    "postgresql://travelinsight_db_user:Js0QSu3ilo6P3ye0LlpIn3ee4LwisZ2E@dpg-d221vhje5dus7396s19g-a/travelinsight_db")
conn = psycopg2.connect(DATABASE_URL)

# 1) Asegurarnos de que la tabla existe
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
    """)
    conn.commit()

# 2) Endpoint POST para guardar respuestas
@app.route("/api/formulario", methods=["POST"])
def guardar_formulario():
    data = request.get_json(force=True)
    # Validación básica
    for key in ("viajas_con", "interes_viaje", "duracion_viaje", "clima_preferencia"):
        if key not in data:
            return jsonify({"error": f"Falta campo '{key}'"}), 400

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO respuestas_formulario 
              (viajas_con, interes_viaje, duracion_viaje, clima_preferencia)
            VALUES (%s, %s, %s, %s);
        """, (
            data["viajas_con"],
            data["interes_viaje"],
            data["duracion_viaje"],
            data["clima_preferencia"]
        ))
        conn.commit()

    return jsonify({"mensaje": "✅ Formulario registrado"}), 201

# 3) Opcional: GET para consultar todas las respuestas
@app.route("/api/formulario", methods=["GET"])
def leer_formularios():
    with conn.cursor() as cur:
        cur.execute("SELECT id, viajas_con, interes_viaje, duracion_viaje, clima_preferencia, fecha FROM respuestas_formulario ORDER BY fecha DESC;")
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    # Transformar a lista de dicts
    resultados = [dict(zip(cols, row)) for row in rows]
    return jsonify(resultados)

# --- Tus endpoints existentes ---
@app.route("/")
def index():
    return "✅ API Travel Insight en Render funcionando"

@app.route("/api/destinos")
def destinos():
    return jsonify(df.head(10).to_dict(orient="records"))

@app.route("/api/municipios")
def municipios():
    return jsonify(df["MUNICIPIO"].dropna().unique().tolist())

@app.route("/api/categorias")
def categorias():
    return jsonify(df["CATEGORIA"].dropna().unique().tolist())

@app.route("/api/destinos/<municipio>")
def destinos_por_municipio(municipio):
    filtro = df[df["MUNICIPIO"].str.lower() == municipio.lower()]
    return jsonify(filtro.to_dict(orient="records"))

@app.route("/api/top-municipios")
def top_municipios():
    return jsonify(df["MUNICIPIO"].value_counts().head(5).to_dict())

@app.route("/api/categoria/<nombre>")
def por_categoria(nombre):
    filtro = df[df["CATEGORIA"].str.lower() == nombre.lower()]
    return jsonify(filtro.to_dict(orient="records"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
