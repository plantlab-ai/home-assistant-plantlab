# PlantLab Home Assistant agent instructions

Use the `ha-plantlab` Conda environment for tests. Run `conda run -n ha-plantlab python -m pytest tests/ -q` before each commit. Run Ruff on `custom_components/` and `tests/`.

Read `docs/model1-species-cutover.md` before changing diagnosis sensors. Compare each API field with `plantlab-go/internal/handlers/diagnose.go` in the PlantLab repository. The client reads one response shape, schema 4.1.0: `species`, `species_confidence`, `species_name`, `in_scope`, `routed_reason`, and `results`. It keeps no legacy or version fallback.

Every in-scope species (cannabis, tomato) gets a health verdict, conditions, and pests. Out-of-scope results show no verdict. Keep the existing cannabis entity IDs and health states.

Update `strings.json`, English and German translations, tests, `manifest.json`, and `CHANGELOG.md` when you change an entity. Before a GitHub operation, run `gh auth switch --user plantlab-ai`.
