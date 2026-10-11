"""Exercise the actual Streamlit demo and the primary validation path."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import data


APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.delenv("PROPERATI_ALLOW_UPLOADS", raising=False)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    return app


def test_demo_starts_with_author_declaration_and_uploads_disabled(demo):
    assert any("Dataset ficticio proporcionado por el autor" in element.value for element in demo.info)
    assert any("no verificado de forma independiente" in element.value for element in demo.info)
    assert not demo.get("file_uploader")
    assert not demo.radio
    assert any("Cobertura" in metric.label for metric in demo.metric)
    frame, _ = data.load_demo()
    train, test, _ = data.split_data(frame, test_fraction=0.2, seed=42)
    expected_counts = f"{len(train):,} registros para entrenamiento".replace(",", ".")
    assert any(expected_counts in element.value for element in demo.caption)
    assert not any("sintética" in element.value.lower() for element in demo.info)


def test_demo_form_predicts_and_keeps_dataset_labels(demo):
    demo.button[0].click().run()
    assert not demo.exception
    assert any(metric.label == "Precio estimado del dataset por m²" for metric in demo.metric)
    assert any(metric.label == "Total implícito según la superficie ingresada" for metric in demo.metric)
    assert any("declarado ficticio por el autor" in element.value for element in demo.info)


def test_covered_area_larger_than_total_shows_error_without_prediction(demo):
    inputs = {element.label: element for element in demo.number_input}
    inputs["Superficie total (m²)"].set_value(80.0)
    inputs["Superficie cubierta (m²)"].set_value(120.0)
    demo.button[0].click().run()
    assert not demo.exception
    assert any("no puede superar" in element.value for element in demo.error)
    assert not any(metric.label == "Precio estimado del dataset por m²" for metric in demo.metric)


def test_upload_requires_environment_opt_in_and_acknowledgement(monkeypatch):
    monkeypatch.setenv("PROPERATI_ALLOW_UPLOADS", "1")
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio[0].set_value("Cargar mis datos").run()
    assert not app.exception
    assert not app.get("file_uploader")
    assert any("servidor" in element.value for element in app.info)
    assert not any("Dataset ficticio proporcionado por el autor" in element.value for element in app.info)
    assert any("no se aplica" in element.value for element in app.caption)
    app.checkbox[0].check().run()
    assert not app.exception
    assert len(app.get("file_uploader")) == 1


def test_invalid_author_projection_stops_without_generated_fallback(monkeypatch):
    monkeypatch.delenv("PROPERATI_ALLOW_UPLOADS", raising=False)

    def unavailable_projection():
        raise data.DataValidationError("Unavailable test projection")

    def forbidden_generator(*args, **kwargs):
        pytest.fail("The app must not replace the author's dataset with generated data")

    monkeypatch.setattr(data, "load_demo", unavailable_projection)
    monkeypatch.setattr(data, "synthetic_data", forbidden_generator)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert any("No pudimos cargar la proyección" in element.value for element in app.error)
    assert not app.button
