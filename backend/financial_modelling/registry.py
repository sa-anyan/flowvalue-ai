"""One engine, source/policy selection only; no parallel methodology calculations."""

MODEL = {
    "id": "garrett",
    "default": True,
    "source": "Donald E. Garrett, Chemical Engineering Economics (1989), Chapters 5–6; annual timing conventions selected explicitly",
    "status": "preliminary_implemented",
}


def get_model(model_id="garrett"):
    if model_id != "garrett":
        raise ValueError("Unsupported financial methodology: " + str(model_id))
    return dict(MODEL)


def list_models():
    return [get_model()]
