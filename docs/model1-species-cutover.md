# Model 1 species client

The API response uses `species`, `species_confidence`, `species_name`, `in_scope`, and `routed_reason`. Each result carries health, conditions, and pests for every in-scope species. The integration reads only this shape (schema 4.1.0) and keeps no legacy fallback.

The species sensor reports the detected species (for example `cannabis` or `tomato`) or `unknown`. The health sensor reports `healthy` or `unhealthy` for an in-scope plant and `out_of_scope` for a reject. Plant count is the number of results and is zero for a reject. History counts a health result only for items that carry `is_healthy`.
