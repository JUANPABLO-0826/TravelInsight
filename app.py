from flask import Flask, jsonify
import pandas as pd
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

df = pd.read_csv("rnt_limpio.csv")

@app.route("/")
def index():
    return "✅ API Travel Insight en Render funcionando"

@app.route("/api/destinos")
def destinos():
    data = df.head(10).to_dict(orient="records")
    return jsonify(data)

@app.route("/api/municipios")
def municipios():
    municipios = df["MUNICIPIO"].dropna().unique().tolist()
    return jsonify(municipios)

@app.route("/api/categorias")
def categorias():
    cats = df["CATEGORIA"].dropna().unique().tolist()
    return jsonify(cats)

@app.route("/api/destinos/<municipio>")
def destinos_por_municipio(municipio):
    filtro = df[df["MUNICIPIO"].str.lower() == municipio.lower()]
    return jsonify(filtro.to_dict(orient="records"))

@app.route("/api/top-municipios")
def top_municipios():
    top = df["MUNICIPIO"].value_counts().head(5).to_dict()
    return jsonify(top)

# Filtrar por categoría
@app.route("/api/categoria/<nombre>")
def por_categoria(nombre):
    try:
        filtro = df[df["CATEGORIA"].str.lower() == nombre.lower()]
        return jsonify(filtro.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
