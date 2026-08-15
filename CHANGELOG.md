# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- The `problem` binary sensor no longer fires for images that are not cannabis. Stage 1A rejects the image before health is ever assessed, but the API sent `is_healthy: false` on that exit (fixed API-side in v1.0.167), so `not is_healthy` reported "problem detected" for a photo of a pot, a lamp or a coffee mug. The sensor now checks `is_cannabis` first and reports unknown, and keeps doing so against an older API.
- `sensor.plantlab_plant_count` reported `1` for a non-cannabis image. The API wraps even a Stage-1A rejection as one whole-frame result entry, so counting `results[]` counted a plant that was never detected. Now `0` when `is_cannabis` is false.
- The 24-hour history stats counted every non-cannabis diagnosis as **unhealthy**. `/history` reports `is_healthy` as a plain bool, so those entries read `false`; they are now excluded from the healthy/unhealthy split while still counting toward the total.

### Changed

- The `DIAGNOSE_RESPONSE_NOT_CANNABIS` test fixture used `"results": []`, which the API never sends -- it always returns at least one entry. Corrected to the real wire shape, which is what exposed the plant-count bug. A legacy fixture carrying the pre-v1.0.167 `is_healthy: false` is kept so the guards stay honest against an older API.

## [0.8.0] - 2026-07-22

### Added

- New sensor `sensor.plantlab_likely_area` surfaces the PlantLab API schema 3.1.0 `coarse_fallback` field: when the specific (fine-class) diagnosis is below the API's confidence threshold, the response carries the clinical coarse group (mobile-nutrient, new-growth nutrient, watering/root-zone, light/heat, fungal/viral disease, or pest) instead of asserting an uncertain specific label. State is the group key, or `none` when the API was confident. Lets automations react when the diagnosis is only reliable at the group level. German translation included (`Wahrscheinlicher Bereich`).
- The `conditions` and `pests` sensors now expose a per-item `coarse_group` in their attribute lists (schema 3.1.0), so each detected condition/pest can be hedged to its clinical group.

### Changed

- Test fixtures updated to schema 3.1.0. The additions are non-breaking: an older API that omits `coarse_group`/`coarse_fallback` yields null/`none`, so the integration keeps working against an as-yet-unupgraded server.

## [0.7.0] - 2026-06-29

### Changed

- Migrated to PlantLab API schema 3.0.0. The diagnose response is now per-plant: health, growth stage, conditions, pests, nutrient (Mulder's) analysis, reliability and uncertainty fields moved out of the top level into a `results[]` array, one entry per detected plant (each carrying a normalized `bbox`). Image-level fields (`is_cannabis`, `cannabis_confidence`, `engine_version`) stay at the top level. The existing sensors now surface the **primary (first) plant** via `results[0]`; behavior for the common single-plant photo is unchanged.
- The integration tolerates a pre-3.0.0 (flat) response during a staged rollout: when a payload has no `results` key, the per-plant sensors fall back to reading the top-level fields, so an updated integration keeps working against an as-yet-unupgraded API.

### Added

- New diagnostic sensor `sensor.plantlab_plant_count` reports the number of plants the last diagnosis detected (`len(results)`; `0` for a not-cannabis image). Lets automations notice when a frame held more than one plant — only the primary plant is broken out across the other sensors. German translation included (`Anzahl Pflanzen`).

## [0.6.0] - 2026-05-08

### Added

- New diagnostic sensor `sensor.plantlab_history_activity` polls `GET /history` every 30 minutes and exposes diagnosis activity metrics: count of diagnoses in the last 24 hours (state), healthy/unhealthy split for 24h, total 7-day count, most-recent diagnosis timestamp, and a `tier_unavailable` flag when the endpoint returns 403 (free tier or training opt-in disabled). On 403 the sensor reports state `0` with `tier_unavailable=true` — no error state or log spam.
- New `async_get_history` method on `PlantLabApiClient` with a 5-second timeout and `PlantLabTierError` for 403 responses.
- `HistoryCoordinator` (`coordinator.py`) — separate `DataUpdateCoordinator` with a 30-minute polling interval, retry-once semantics on transient failures (leaves previous state on `UpdateFailed`), and a one-shot info log for the tier-unavailable case.
- German translation for the new sensor (`Diagnoseaktivität`).

## [0.5.0] - 2026-05-07

### Added

- New diagnostic sensor `sensor.plantlab_engine_version` exposes the API build that served the last diagnosis (state) and the global model iteration label as a `models` attribute. Lets automations detect when PlantLab ships a new engine and react (e.g. invalidate caches, recompute thresholds, log the transition). Surfaces the `engine_version` block introduced by API schema 2.1.0.

### Changed

- Bumped supported PlantLab API schema to 2.1.0 (additive: new optional `engine_version` field). Older API responses without the field continue to work; the new sensor reports `unknown`.
- German translation added for the new sensor (`Engine-Version` / `Modelle`).

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
