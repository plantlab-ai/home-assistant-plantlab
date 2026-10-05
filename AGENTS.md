# PlantLab Home Assistant agent instructions

Use the `ha-plantlab` Conda environment for tests. Run `conda run -n ha-plantlab python -m pytest tests/ -q` before each commit. Run Ruff on `custom_components/` and `tests/`.

Read `docs/model1-species-cutover.md` before changing diagnosis sensors. Compare each API field with `plantlab-go/internal/handlers/diagnose.go` in the PlantLab repository. The client reads API schemas 3.1.0 and 4.0.0. Schema 4.0.0 uses `species`, `species_confidence`, `in_scope`, and `routed_reason`. It does not send the old cannabis yes/no fields.

Only cannabis gets a health diagnosis. Tomato and out-of-scope results stop after species detection. Do not show a health, problem, condition, pest, or nutrient verdict for either result. Keep the existing cannabis entity IDs and health states.

Update `strings.json`, English and German translations, tests, `manifest.json`, and `CHANGELOG.md` when you change an entity. Before a GitHub operation, run `gh auth switch --user plantlab-ai`.
