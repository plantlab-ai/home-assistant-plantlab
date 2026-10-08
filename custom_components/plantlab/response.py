def detected_species(data: dict | None) -> str | None:
    if not data or not data.get("in_scope"):
        return None
    return data.get("species")


def species_confidence(data: dict | None) -> float | None:
    if detected_species(data) is None:
        return None
    return data.get("species_confidence")


def has_diagnosis(data: dict) -> bool:
    return bool(data.get("results"))


def prediction_name(prediction: dict) -> str:
    return prediction.get("display_name", prediction.get("class_id", "unknown"))


def is_suspected(prediction: dict) -> bool:
    return prediction.get("suspected") is True


def prediction_state(predictions: list[dict]) -> str:
    if not predictions:
        return "none"
    top = predictions[0]
    name = prediction_name(top)
    return f"Suspected: {name}" if is_suspected(top) else name
