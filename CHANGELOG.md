# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
