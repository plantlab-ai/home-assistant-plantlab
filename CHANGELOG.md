# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] - 2026-04-29

### Changed

- Migrated to PlantLab API schema 2.0.0. The integration now consumes `reliability_score` (Stage 2 output, optional 0-1 float) in place of the removed `diagnostic_confidence` and `safety_classification` fields.
- Renamed `sensor.plantlab_diagnostic_confidence` to `sensor.plantlab_reliability_score`. The percentage state behaves as before (0-100%), and a derived `reliability_label` attribute (`confident` >= 70%, `uncertain` >= 30%, otherwise `low_confidence`) replaces the previous `safety_classification` attribute.
- Conditions and Pests sensor `confidence` attribute renamed to `reliability_score` for consistency with the new schema.

### Breaking

- Entity ID change: `sensor.plantlab_diagnostic_confidence` no longer exists. Users with dashboards or automations referencing the old entity must update them to `sensor.plantlab_reliability_score`. Removing and re-adding the integration is the cleanest path; otherwise the old entity will linger as unavailable in the entity registry.
- The `safety_classification` attribute is gone. Automations reading it should switch to either the numeric state of `sensor.plantlab_reliability_score` or the new `reliability_label` attribute.
- When the API response omits `reliability_score` (for example, against a 1.x server, or when Stage 2 did not run), the sensor reports `unknown` rather than crashing.

## [0.3.1] - 2026-04-16

### Fixed

- Formatted `tests/test_translations.py` to satisfy Ruff format checks and restore passing CI for the translation test additions released in `v0.3.0`.

## [0.3.0] - 2026-04-16

### Added

- Promoted `severity`, `treatment_steps`, and inline `confidence` attributes on the Conditions and Pests sensors for cleaner Home Assistant card rendering.
- German (`de`) translations for entity names, states, attributes, and config flow copy, alongside complete English translation catalogs.
- Translation integrity and fallback tests covering German loading, English fallback for unsupported or incomplete languages, and required translation key coverage.

## [0.2.0] - 2026-04-15

### Added

- `sensor.plantlab_diagnostic_confidence` — overall diagnosis confidence as a percentage (0-100%). Attributes include `safety_classification` and `uncertainty_factors` for automation use.

## [0.1.1] - 2026-03-26

### Added

- `sensor.plantlab_nutrient_analysis` — surfaces Mulders Chart antagonism analysis from the API, showing the most likely excess nutrient causing detected deficiencies (state: top hypothesis, attributes: full ranked list)

## [0.1.0] - 2026-03-26

### Added

- Config flow with API key validation via `/info` endpoint
- `plantlab.diagnose` service action accepting camera entity or image file path
- Response data returned via `response_variable` for automation chains
- Sensor entities: health, conditions, pests, growth stage
- Binary sensor: problem detection (on when unhealthy)
- Dispatcher-based sensor updates (event-driven, no polling)
- Rate limit handling for free tier (3 diagnoses/day)
- HACS compatibility
