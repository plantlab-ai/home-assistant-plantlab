# PlantLab for Home Assistant

[![CI](https://github.com/plantlab-ai/home-assistant-plantlab/actions/workflows/tests.yml/badge.svg)](https://github.com/plantlab-ai/home-assistant-plantlab/actions/workflows/tests.yml)

Plant health diagnosis for Home Assistant. Point a camera at your cannabis plant, and PlantLab tells you what's wrong - nutrient deficiencies, pests, diseases, growth stage, and nutrient antagonism analysis via Mulder's Chart.

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
| `sensor.plantlab_health` | Overall health: healthy / unhealthy / not_cannabis |
| `sensor.plantlab_conditions` | Top detected condition (e.g., Nitrogen Deficiency) |
| `sensor.plantlab_pests` | Top detected pest (e.g., Spider Mites) |
| `sensor.plantlab_growth_stage` | Growth stage: vegetative / flowering / seedling |
| `sensor.plantlab_nutrient_analysis` | Mulder's Chart nutrient antagonism hypothesis (e.g., Potassium Excess) |
| `binary_sensor.plantlab_problem` | On when plant is unhealthy |

## Free Tier

PlantLab's free tier gives you 3 diagnoses per day - one morning check, one evening, and a spare for when you're feeling paranoid.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
