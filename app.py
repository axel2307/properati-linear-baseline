"""Streamlit interface for a small OLS baseline on the author's dataset."""

import os

import numpy as np
import pandas as pd
import streamlit as st

from data import DataValidationError, load_csv, load_demo, split_data
from model import ModelValidationError, fit_model


REASONS = {
    "invalid_features": "Superficies, ambientes o proporción inválidos",
    "unknown_property_type": "Tipo de propiedad sin ejemplos de entrenamiento",
    "unknown_neighborhood": "Barrio sin ejemplos de entrenamiento",
    "unseen_category_combination": "Combinación de barrio y tipo sin ejemplos",
    "outside_training_range": "Valores fuera del rango de entrenamiento",
    "nonpositive_or_nonfinite_prediction": "El modelo produjo un precio inválido",
    "invalid_target": "Precio observado inválido",
}
FEATURE_LABELS = {"rooms": "Ambientes", "area_total": "Superficie total (m²)", "ratio": "Proporción cubierta"}
PROPERTY_LABELS = {"apartment": "Departamento", "house": "Casa", "PH": "PH"}
REPOSITORY_URL = "https://github.com/axel2307/properati-linear-baseline"


def money(value: float) -> str:
    return f"USD {value:,.0f}".replace(",", ".")


st.set_page_config(page_title="Properati · Regresión lineal", page_icon="🏠", layout="centered")
st.title("Precios del dataset: regresión lineal")
st.write("Ingresá las características de una propiedad para estimar su precio por m².")

allow_uploads = os.getenv("PROPERATI_ALLOW_UPLOADS", "0") == "1"
source = "Demo del autor"
if allow_uploads:
    source = st.radio("Datos para explorar", ["Demo del autor", "Cargar mis datos"], horizontal=True)

report = None
if source == "Demo del autor":
    st.caption("Demo educativa con datos ficticios")
    try:
        frame, report = load_demo()
    except (DataValidationError, ValueError, OSError):
        st.error("No pudimos cargar la proyección del autor incluida en la demo. Revisá que data/demo.csv esté disponible y sea válido.")
        st.stop()
else:
    st.info("El archivo se enviará al servidor de esta app.")
    st.caption(f"[Privacidad y uso de archivos]({REPOSITORY_URL}/blob/main/PRIVACY.md)")
    acknowledged = st.checkbox("Revisé la licencia y la privacidad del archivo, y autorizo su envío a este servidor.")
    if not acknowledged:
        st.stop()
    uploaded = st.file_uploader("Elegí un CSV o TSV compatible", type=["csv", "tsv"], help="No hacen falta direcciones, contactos, descripciones ni enlaces de avisos. Se usan sólo las columnas necesarias para el modelo.")
    if uploaded is None:
        st.stop()
    try:
        frame, report = load_csv(uploaded)
    except (DataValidationError, ValueError, UnicodeError):
        st.error("No pudimos validar el archivo. Revisá el esquema y los requisitos del README: tipo, barrio, superficies, ambientes, ubicación aproximada y precio en USD.")
        st.stop()

try:
    train, test, split_info = split_data(frame, test_fraction=0.2, seed=42)
    fitted = fit_model(train)
    evaluation = fitted.evaluate(test)
except (DataValidationError, ModelValidationError, ValueError):
    st.error("No hay suficientes datos válidos y diversos para separar ubicaciones y entrenar el modelo. Revisá los requisitos del README o probá la demo.")
    st.stop()

st.caption(f"{len(train):,} registros para entrenamiento · {len(test):,} para evaluación".replace(",", "."))
if fitted.rank_deficient or fitted.condition_number > 1e8:
    st.warning("La matriz tiene redundancia o inestabilidad. Los coeficientes no deben interpretarse como efectos independientes; revisá los diagnósticos al final de la página.")
st.subheader("Probá una propiedad")

default_total = float(np.clip(100.0, fitted.lower["area_total"], fitted.upper["area_total"]))
default_ratio = float(np.clip(0.8, fitted.lower["ratio"], fitted.upper["ratio"]))
default_rooms = int(np.clip(3, fitted.lower["rooms"], fitted.upper["rooms"]))
default_type, default_neighborhood = sorted(fitted.category_pairs)[0]
with st.form("property_query"):
    property_type = st.selectbox("Tipo de propiedad", fitted.categories["property_type"], index=fitted.categories["property_type"].index(default_type), format_func=lambda value: PROPERTY_LABELS.get(value, value))
    neighborhood = st.selectbox("Barrio", fitted.categories["neighborhood"], index=fitted.categories["neighborhood"].index(default_neighborhood))
    rooms = st.number_input("Ambientes", min_value=1, value=default_rooms, step=1)
    area_total = st.number_input("Superficie total (m²)", min_value=0.1, value=round(default_total, 1), step=1.0)
    area_covered = st.number_input("Superficie cubierta (m²)", min_value=0.1, value=round(default_total * default_ratio, 1), step=1.0)
    submitted = st.form_submit_button("Estimar precio del dataset", type="primary", width="stretch")

if submitted:
    if area_covered > area_total:
        st.error("La superficie cubierta no puede superar la superficie total. Corregí las superficies y volvé a probar.")
    else:
        query = pd.DataFrame([{
            "property_type": property_type, "neighborhood": neighborhood,
            "rooms": rooms, "area_total": area_total,
            "area_covered": area_covered, "ratio": area_covered / area_total,
        }])
        prediction = fitted.predict(query).iloc[0]
        if not prediction["supported"]:
            st.warning("No podemos dar una estimación para estos valores: " + REASONS[prediction["reason"]].lower() + ".")
            st.caption("Consultá los rangos de entrenamiento al final de la página. No se ajustan ni se recortan tus valores automáticamente.")
        else:
            st.metric("Precio estimado del dataset por m²", money(prediction["predicted_usd_m2"]))
            st.metric("Total implícito según la superficie ingresada", money(prediction["predicted_price_usd"]))
            st.caption("Total = precio por m² × superficie total.")

st.subheader("Evaluación con registros reservados")
st.metric("Cobertura en evaluación", f"{100 * evaluation['coverage']:.1f}%", help="Porcentaje de registros reservados con categorías, combinaciones y rangos admitidos, y una predicción positiva y finita.")
st.caption(f"{evaluation['supported_rows']} de {evaluation['total_rows']} registros reservados admitidos. Modelo y referencia se comparan sobre esos mismos registros.")
if evaluation["supported_rows"]:
    results = pd.DataFrame([
        {"Método": "Regresión lineal", "Error absoluto medio (USD/m²)": evaluation["mae_usd_m2"], "Mediana del error absoluto (USD/m²)": evaluation["median_ae_usd_m2"]},
        {"Método": "Mediana del entrenamiento", "Error absoluto medio (USD/m²)": evaluation["baseline_mae_usd_m2"], "Mediana del error absoluto (USD/m²)": evaluation["baseline_median_ae_usd_m2"]},
    ])
    st.dataframe(results, hide_index=True, width="stretch", column_config={
        "Error absoluto medio (USD/m²)": st.column_config.NumberColumn(format="%.1f"),
        "Mediana del error absoluto (USD/m²)": st.column_config.NumberColumn(format="%.1f"),
    })
    if evaluation["supported_rows"] < 30:
        st.warning("Hay menos de 30 registros admitidos en evaluación; tomá estas métricas con especial cautela.")
else:
    st.warning("No hay registros reservados compatibles. No se pueden calcular métricas honestas para este conjunto.")
if evaluation["excluded_reasons"]:
    with st.expander("Registros fuera de la evaluación"):
        for reason, count in evaluation["excluded_reasons"].items():
            st.write(f"- {REASONS.get(reason, reason)}: {count}")

with st.expander("Rangos y diagnósticos"):
    ranges = pd.DataFrame([
        {"Variable": FEATURE_LABELS[column], "Mínimo aprendido": fitted.lower[column], "Máximo aprendido": fitted.upper[column]}
        for column in FEATURE_LABELS
    ])
    st.dataframe(ranges, hide_index=True, width="stretch")
    st.caption(f"Columnas del modelo: {len(fitted.feature_names)} · Rango de la matriz: {fitted.rank}")
    condition = "infinito" if not np.isfinite(fitted.condition_number) else f"{fitted.condition_number:,.1f}"
    st.caption(f"Número de condición: {condition}")

st.caption(f"[Metodología, datos y límites]({REPOSITORY_URL}#readme)")
