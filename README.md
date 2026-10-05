# PlantLab for Home Assistant

[![CI](https://github.com/plantlab-ai/home-assistant-plantlab/actions/workflows/tests.yml/badge.svg)](https://github.com/plantlab-ai/home-assistant-plantlab/actions/workflows/tests.yml)

PlantLab identifies cannabis and tomato images in Home Assistant. It diagnoses cannabis health, including nutrient deficiencies, pests, diseases, and growth stage. Tomato detection does not include a health diagnosis yet.

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "PlantLab" and install
3. Restart Home Assistant

### Manual

Copy the `custom_components/plantlab` directory to your Home Assistant `config/custom_components/` directory.

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "PlantLab"
3. Enter your API key (get one free at [plantlab.ai](https://plantlab.ai))

## Usage

### Service Action

Call `plantlab.diagnose` with a camera entity or image file path:

```yaml
# From a camera entity
action: plantlab.diagnose
data:
  entity_id: camera.grow_tent
response_variable: diagnosis

# From a file path
action: plantlab.diagnose
data:
  image_path: /config/www/plant_snapshot.jpg
response_variable: diagnosis
```

### Example Automation

```yaml
automation:
  - alias: "Daily Plant Health Check"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - action: camera.snapshot
        target:
          entity_id: camera.grow_tent
        data:
          filename: /config/www/plant_snapshot.jpg
      - action: plantlab.diagnose
        data:
          image_path: /config/www/plant_snapshot.jpg
        response_variable: diagnosis
      - if: "{{ diagnosis.is_healthy == false }}"
        then:
          - action: notify.mobile_app
            data:
              title: "Plant Health Alert"
              message: >
                Issues detected: {{ diagnosis.conditions | map(attribute='display_name') | join(', ') }}
```

### Sensors

After your first diagnosis, these entities become available:

| Entity | Description |
|--------|-------------|
| `sensor.plantlab_species` | Cannabis, tomato, or unknown species; includes confidence and routing fields |
| `sensor.plantlab_health` | Cannabis health; tomato detection or out-of-scope status has no health verdict |
| `sensor.plantlab_conditions` | Top detected condition (e.g., Nitrogen Deficiency) |
| `sensor.plantlab_pests` | Top detected pest (e.g., Spider Mites) |
| `sensor.plantlab_growth_stage` | Growth stage: vegetative / flowering / seedling |
| `sensor.plantlab_nutrient_analysis` | Mulder's Chart nutrient antagonism hypothesis (e.g., Potassium Excess) |
| `sensor.plantlab_likely_area` | Clinical group when the specific diagnosis is uncertain (e.g., Mobile-nutrient issue); `none` when confident |
| `binary_sensor.plantlab_problem` | On when plant is unhealthy |

The integration reads API schemas 3.1.0 and 4.0.0. Install version 0.9.0 before the API switches to schema 4.0.0. The `plantlab.diagnose` service returns the API response unchanged. In schema 4.0.0, `species` replaces the old cannabis flag. Existing cannabis entity IDs and health states stay the same. The health sensor now exposes species attributes instead of the old cannabis yes/no attributes.

For tomato, the health sensor reports `tomato_detected`, the problem sensor stays unknown, and plant count stays unknown. For a schema 4.0.0 reject, health reports `out_of_scope` and plant count reports zero. A schema 3.1.0 reject keeps the `not_cannabis` health state.

## Free Tier

PlantLab's free tier gives you 3 diagnoses per day - one morning check, one evening, and a spare for when you're feeling paranoid.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
