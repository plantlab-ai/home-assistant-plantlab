def detected_species(data: dict | None) -> str | None:
    if not data:
        return None
    if "species" in data:
        species = data["species"]
        return species if species in ("cannabis", "tomato") else None
    return "cannabis" if data.get("is_cannabis") is True else None


def species_confidence(data: dict | None) -> float | None:
    if not data or detected_species(data) is None:
        return None
    if "species" in data:
        return data.get("species_confidence")
    return data.get("cannabis_confidence")


def has_diagnosis(data: dict) -> bool:
    if "species" not in data:
        return True
    return detected_species(data) == "cannabis" and bool(data.get("results"))
