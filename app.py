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


def money(value: float) -> str:
    return f"USD {value:,.0f}".replace(",", ".")


st.set_page_config(page_title="Properati · Regresión lineal", page_icon="🏠", layout="centered")
st.title("Precios del dataset: regresión lineal")
st.write("Explorá un modelo artesanal que relaciona características de una propiedad con el precio por m² registrado en el dataset.")
st.warning("Es un ejercicio educativo. No es una tasación, un precio de cierre ni una estimación del valor actual.")

allow_uploads = os.getenv("PROPERATI_ALLOW_UPLOADS", "0") == "1"
source = "Demo del autor"
if allow_uploads:
    source = st.radio("Datos para explorar", ["Demo del autor", "Cargar mis datos"], horizontal=True)
else:
    st.caption("Esta versión usa una proyección autorizada del archivo del autor. Las cargas están deshabilitadas por defecto; el README explica cómo habilitarlas en una instalación propia.")

report = None
if source == "Demo del autor":
    st.info("Dataset ficticio proporcionado por el autor. Declaración del autor; no verificado de forma independiente. No representa precios de mercado.")
    st.caption("La demo conserva sólo ocho campos necesarios; las coordenadas se redondearon a tres decimales y los registros se validaron y deduplicaron de nuevo.")
    try:
        frame, report = load_demo()
    except (DataValidationError, ValueError, OSError):
        st.error("No pudimos cargar la proyección del autor incluida en la demo. Revisá que data/demo.csv esté disponible y sea válido.")
        st.stop()
else:
    st.info("Al cargar un archivo, tu navegador lo envía al servidor donde corre esta app. Usala localmente para datos privados. No guardamos el archivo en disco ni lo incluimos en cachés de la app.")
    st.caption("La declaración de ficción de la demo no se aplica a los archivos que cargues. Revisá su procedencia, privacidad y significado antes de interpretar los resultados.")
    acknowledged = st.checkbox("Revisé la licencia y la privacidad del archivo, y autorizo su envío a este servidor.")
    if not acknowledged:
        st.caption("Revisá el aviso anterior para habilitar la carga.")
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

st.caption(f"{len(train):,} registros para entrenamiento · {len(test):,} para evaluación. El formulario usa únicamente el modelo de entrenamiento.".replace(",", "."))
if fitted.rank_deficient or fitted.condition_number > 1e8:
    st.warning("La matriz tiene redundancia o inestabilidad. Los coeficientes no deben interpretarse como efectos independientes; revisá los diagnósticos al final de la página.")
if report is not None:
    with st.expander("Calidad de los datos usados"):
        st.write(f"Filas recibidas: {report['input_rows']:,}. Filas aceptadas: {report['accepted_rows']:,}.".replace(",", "."))
        st.write(f"Filas rechazadas: {report['rejected_rows']:,}. Duplicados retirados: {report['duplicate_rows_removed']:,}.".replace(",", "."))
        st.caption("Se muestran cantidades agregadas; no se muestran registros individuales, direcciones ni coordenadas.")

st.subheader("Probá una propiedad")
st.write("Elegí categorías que el modelo haya visto. Si los valores se salen de su rango o la combinación no tiene ejemplos, la app te lo va a indicar.")

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
    st.caption("La proporción cubierta se calcula como superficie cubierta / total. Baños y comodidades no forman parte de este modelo.")
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
            st.caption("El total es el precio por m² multiplicado por la superficie total. No constituye una segunda estimación independiente. No mostramos un intervalo de confianza: este ejercicio no lo ha validado.")
            if source == "Demo del autor":
                st.info("Resultado sobre el dataset declarado ficticio por el autor. Sirve para explorar el modelo y no representa precios de mercado.")

st.subheader("Evaluación con registros reservados")
st.write("La evaluación reserva grupos de ubicación completos antes de aprender columnas, escalas y coeficientes. Se retiran duplicados antes de separar los datos. No se presume una fecha confiable para los registros.")
if source == "Demo del autor":
    st.caption("Estas métricas describen sólo la proyección del dataset declarado ficticio por el autor. No miden precisión en el mercado inmobiliario.")
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
    st.caption("Errores más bajos son mejores. Esta comparación no incluye los registros rechazados y no permite inferir el rendimiento sobre ellos ni sobre otros datasets.")
    if evaluation["supported_rows"] < 30:
        st.warning("Hay menos de 30 registros admitidos en evaluación; tomá estas métricas con especial cautela.")
else:
    st.warning("No hay registros reservados compatibles. No se pueden calcular métricas honestas para este conjunto.")
if evaluation["excluded_reasons"]:
    with st.expander("Registros fuera de la evaluación"):
        for reason, count in evaluation["excluded_reasons"].items():
            st.write(f"- {REASONS.get(reason, reason)}: {count}")

with st.expander("Cómo funciona y cuáles son sus límites"):
    st.write("La regresión aprende el precio registrado en el dataset en USD/m² a partir de ambientes, superficie total, proporción cubierta, tipo y barrio. Se resuelve con mínimos cuadrados (`numpy.linalg.lstsq`), con variables numéricas estandarizadas, un único intercepto y una categoría de referencia por variable.")
    st.write("La mediana de referencia se calcula sólo en entrenamiento. Los datos reservados no ajustan coeficientes, columnas, escalas ni rangos. El modelo tampoco se vuelve a entrenar con ellos después de mostrar las métricas.")
    st.write("La separación por celdas geográficas reduce parte de la filtración entre ubicaciones, pero no es un bloqueo por distancia con zona de exclusión: ubicaciones cercanas a un borde pueden quedar en grupos distintos. No garantiza independencia temporal ni elimina todos los registros repetidos. Redondear coordenadas también cambia la asignación de algunos grupos y la detección de duplicados.")
    st.write("El modelo lineal simplifica relaciones y omite estado de conservación, antigüedad, piso, orientación, calidad y otras variables. Las categorías conocidas y los rangos individuales tampoco garantizan que toda combinación numérica esté bien representada.")
    ranges = pd.DataFrame([
        {"Variable": FEATURE_LABELS[column], "Mínimo aprendido": fitted.lower[column], "Máximo aprendido": fitted.upper[column]}
        for column in FEATURE_LABELS
    ])
    st.dataframe(ranges, hide_index=True, width="stretch")
    st.write(f"Filas de entrenamiento: {fitted.training_rows}. Columnas del modelo: {len(fitted.feature_names)}. Rango de la matriz: {fitted.rank}.")
    condition = "infinito" if not np.isfinite(fitted.condition_number) else f"{fitted.condition_number:,.1f}"
    st.write(f"Número de condición de la matriz estandarizada: {condition}.")
    st.caption("Un rango menor que el número de columnas indica coeficientes no identificables de forma única; un número de condición alto indica sensibilidad numérica.")
    st.write("Referencias categóricas: tipo " + PROPERTY_LABELS.get(fitted.reference_categories["property_type"], fitted.reference_categories["property_type"]) + "; barrio " + fitted.reference_categories["neighborhood"] + ".")
    if fitted.rank_deficient or fitted.condition_number > 1e8:
        st.warning("Hay redundancia o inestabilidad en la matriz. El algoritmo puede calcular una solución, pero no interpretes sus coeficientes como efectos independientes.")

st.caption("Portfolio educativo · Demo con proyección autorizada del autor · Sin proveedores de datos adicionales")
