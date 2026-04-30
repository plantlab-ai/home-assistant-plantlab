import copy
import json
from pathlib import Path

import homeassistant.helpers.translation as translation_helper
from homeassistant.helpers.translation import async_get_translations

from custom_components.plantlab.const import DOMAIN

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = REPO_ROOT / "custom_components" / DOMAIN
TRANSLATIONS_DIR = INTEGRATION_DIR / "translations"
REQUIRED_TRANSLATION_PATHS = {
    "config.step.user.title",
    "config.step.user.description",
    "config.step.user.data.api_key",
    "config.step.user.data.host",
    "config.error.invalid_auth",
    "config.error.cannot_connect",
    "config.abort.already_configured",
    "entity.sensor.health.name",
    "entity.sensor.health.state.healthy",
    "entity.sensor.health.state.unhealthy",
    "entity.sensor.health.state.not_cannabis",
    "entity.sensor.health.state_attributes.confidence.name",
    "entity.sensor.health.state_attributes.is_cannabis.name",
    "entity.sensor.health.state_attributes.cannabis_confidence.name",
    "entity.sensor.conditions.name",
    "entity.sensor.conditions.state.none",
    "entity.sensor.conditions.state_attributes.conditions.name",
    "entity.sensor.conditions.state_attributes.count.name",
    "entity.sensor.conditions.state_attributes.reliability_score.name",
    "entity.sensor.pests.name",
    "entity.sensor.pests.state.none",
    "entity.sensor.pests.state_attributes.pests.name",
    "entity.sensor.pests.state_attributes.count.name",
    "entity.sensor.pests.state_attributes.reliability_score.name",
    "entity.sensor.growth_stage.name",
    "entity.sensor.growth_stage.state.seedling",
    "entity.sensor.growth_stage.state.vegetative",
    "entity.sensor.growth_stage.state.flowering",
    "entity.sensor.growth_stage.state.unknown",
    "entity.sensor.growth_stage.state_attributes.confidence.name",
    "entity.sensor.nutrient_analysis.name",
    "entity.sensor.nutrient_analysis.state.none",
    "entity.sensor.nutrient_analysis.state_attributes.hypotheses.name",
    "entity.sensor.nutrient_analysis.state_attributes.count.name",
    "entity.sensor.reliability_score.name",
    "entity.sensor.reliability_score.state_attributes.reliability_label.name",
    "entity.sensor.reliability_score.state_attributes.reliability_label.state.confident",
    "entity.sensor.reliability_score.state_attributes.reliability_label.state.uncertain",
    "entity.sensor.reliability_score.state_attributes.reliability_label.state.low_confidence",
    "entity.sensor.reliability_score.state_attributes.uncertainty_factors.name",
    "entity.binary_sensor.problem.name",
    "entity.binary_sensor.problem.state_attributes.problems.name",
    "entity.binary_sensor.problem.state_attributes.count.name",
}


def _load_translation_file(path: Path) -> dict:
    return json.loads(path.read_text())


def _leaf_paths(data: dict, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            paths.update(_leaf_paths(value, path))
        else:
            paths.add(path)
    return paths


def _clear_translation_cache(hass) -> None:
    cache = translation_helper._async_get_translations_cache(hass)
    cache.cache_data.loaded.clear()
    cache.cache_data.cache.clear()
    hass.data.pop(translation_helper.TRANSLATION_FLATTEN_CACHE, None)
    translation_helper._async_get_translations_cache.cache_clear()


def test_translation_catalogs_exist_and_match_english_structure():
    english_path = TRANSLATIONS_DIR / "en.json"
    german_path = TRANSLATIONS_DIR / "de.json"
    strings_path = INTEGRATION_DIR / "strings.json"

    assert english_path.exists()
    assert german_path.exists()
    assert strings_path.exists()

    english_catalog = _load_translation_file(english_path)
    german_catalog = _load_translation_file(german_path)
    strings_catalog = _load_translation_file(strings_path)

    english_paths = _leaf_paths(english_catalog)

    assert english_paths >= REQUIRED_TRANSLATION_PATHS
    assert _leaf_paths(german_catalog) == english_paths
    assert _leaf_paths(strings_catalog) == english_paths


async def test_german_translations_are_loaded(hass):
    _clear_translation_cache(hass)

    entity_translations = await async_get_translations(
        hass,
        "de",
        "entity",
        integrations={DOMAIN},
    )
    config_translations = await async_get_translations(
        hass,
        "de",
        "config",
        integrations={DOMAIN},
    )

    assert entity_translations["component.plantlab.entity.sensor.conditions.name"] == "Probleme"
    assert (
        entity_translations["component.plantlab.entity.sensor.conditions.state_attributes.reliability_score.name"]
        == "Verlässlichkeitswert"
    )
    assert config_translations["component.plantlab.config.step.user.title"] == "Mit PlantLab verbinden"


async def test_unsupported_language_falls_back_to_english(hass):
    _clear_translation_cache(hass)

    entity_translations = await async_get_translations(
        hass,
        "fr",
        "entity",
        integrations={DOMAIN},
    )
    config_translations = await async_get_translations(
        hass,
        "fr",
        "config",
        integrations={DOMAIN},
    )

    assert entity_translations["component.plantlab.entity.sensor.conditions.name"] == "Conditions"
    assert (
        entity_translations["component.plantlab.entity.sensor.conditions.state_attributes.reliability_score.name"]
        == "Reliability score"
    )
    assert config_translations["component.plantlab.config.step.user.title"] == "Connect to PlantLab"


async def test_missing_requested_language_key_falls_back_to_english(hass, monkeypatch):
    original_load_json = translation_helper.load_json

    def patched_load_json(path: Path):
        data = original_load_json(path)
        if path.as_posix().endswith(f"custom_components/{DOMAIN}/translations/de.json"):
            data = copy.deepcopy(data)
            del data["entity"]["sensor"]["conditions"]["name"]
        return data

    monkeypatch.setattr(translation_helper, "load_json", patched_load_json)
    _clear_translation_cache(hass)

    entity_translations = await async_get_translations(
        hass,
        "de",
        "entity",
        integrations={DOMAIN},
    )

    assert entity_translations["component.plantlab.entity.sensor.conditions.name"] == "Conditions"
    assert entity_translations["component.plantlab.entity.sensor.health.name"] == "Gesundheit"


async def test_missing_requested_language_file_falls_back_to_english(hass, monkeypatch):
    original_load_json = translation_helper.load_json

    def patched_load_json(path: Path):
        if path.as_posix().endswith(f"custom_components/{DOMAIN}/translations/de.json"):
            return {}
        return original_load_json(path)

    monkeypatch.setattr(translation_helper, "load_json", patched_load_json)
    _clear_translation_cache(hass)

    entity_translations = await async_get_translations(
        hass,
        "de",
        "entity",
        integrations={DOMAIN},
    )
    config_translations = await async_get_translations(
        hass,
        "de",
        "config",
        integrations={DOMAIN},
    )

    assert entity_translations["component.plantlab.entity.sensor.conditions.name"] == "Conditions"
    assert config_translations["component.plantlab.config.step.user.title"] == "Connect to PlantLab"
