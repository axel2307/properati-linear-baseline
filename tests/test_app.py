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


def test_demo_has_one_discreet_legend_and_uploads_disabled(demo):
    assert [element.value for element in demo.caption].count("Demo educativa con datos ficticios") == 1
    assert not demo.info
    assert not demo.warning
    visible_text = "\n".join(element.value for kind in ("caption", "markdown", "info", "warning") for element in demo.get(kind))
    for removed_text in ("Es un ejercicio educativo", "proyección autorizada", "Declaración del autor", "no verificado", "ocho campos", "No representa precios de mercado"):
        assert removed_text not in visible_text
    assert not demo.get("file_uploader")
    assert not demo.radio
    assert any("Cobertura" in metric.label for metric in demo.metric)
    frame, _ = data.load_demo()
    train, test, _ = data.split_data(frame, test_fraction=0.2, seed=42)
    expected_counts = f"{len(train):,} registros para entrenamiento".replace(",", ".")
    assert any(expected_counts in element.value for element in demo.caption)
    assert any("Metodología, datos y límites" in element.value for element in demo.caption)


def test_demo_form_predicts_and_keeps_dataset_labels(demo):
    demo.button[0].click().run()
    assert not demo.exception
    assert any(metric.label == "Precio estimado del dataset por m²" for metric in demo.metric)
    assert any(metric.label == "Total implícito según la superficie ingresada" for metric in demo.metric)
    assert [element.value for element in demo.caption].count("Demo educativa con datos ficticios") == 1
    assert not demo.info


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
    assert not any("datos ficticios" in element.value for element in app.caption)
    assert any("PRIVACY.md" in element.value for element in app.caption)
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
