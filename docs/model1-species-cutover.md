# Model 1 species client plan

Status: local worktree implementation. The PlantLab API cutover is a separate release step.

The API schema 4.0.0 response uses `species`, `species_confidence`, `in_scope`, and `routed_reason`. It returns diagnosis entries only for cannabis. The integration must also read schema 3.1.0 during the release window.

1. Add schema 4.0.0 fixtures for cannabis, tomato, and neither. Keep the schema 3.1.0 fixtures.
2. Write failing sensor and history tests for both versions. Check that tomato and neither have no health or problem verdict.
3. Normalize the two wire formats in one helper. Use that helper in health, problem, plant count, and history views.
4. Add a species sensor. Keep the existing entity IDs and cannabis diagnosis values.
5. Replace the old cannabis flag attributes with species attributes. Update English and German strings and translation tests.
6. Update the version, changelog, README, and `AGENTS.md`. Run the full `ha-plantlab` test suite and lint checks.

The species sensor reports `cannabis`, `tomato`, or `unknown`. The health sensor reports `tomato_detected` for tomato and `out_of_scope` for a schema 4.0.0 reject. A legacy reject keeps `not_cannabis`. Tomato plant count remains unknown because the API does not run the plant slicer for tomato.

Local checks on 2026-10-05: 57 tests passed. Ruff check and format checks passed. The branch is ready for a client release after integration. No tag or public release exists yet.
