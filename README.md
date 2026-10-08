# PlantLab for Home Assistant

[![CI](https://github.com/plantlab-ai/home-assistant-plantlab/actions/workflows/tests.yml/badge.svg)](https://github.com/plantlab-ai/home-assistant-plantlab/actions/workflows/tests.yml)

PlantLab diagnoses cannabis and tomato plants in Home Assistant. Every in-scope plant gets a health verdict, conditions, and pests. Cannabis diagnoses also include growth stage and nutrient analysis.

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
      - variables:
          plant: "{{ diagnosis.results[0] if diagnosis.results else none }}"
      - if: "{{ plant is not none and plant.is_healthy == false }}"
        then:
          - action: notify.mobile_app
            data:
              title: "Plant Health Alert"
              message: >
                {% set suspected = plant.conditions | length > 0 and plant.conditions | selectattr('suspected', 'defined') | selectattr('suspected') | list | length == plant.conditions | length %}
                {{ 'Suspected, low confidence, monitor the plant: ' if suspected else 'Issues detected: ' }}{{ plant.conditions | map(attribute='display_name') | join(', ') }}
```

### Sensors

After your first diagnosis, these entities become available:

| Entity | Description |
|--------|-------------|
| `sensor.plantlab_species` | Detected species (for example cannabis or tomato) or unknown; includes confidence, scientific name, and routing fields |
| `sensor.plantlab_health` | Plant health for any in-scope species; `out_of_scope` when the image shows no supported plant |
| `sensor.plantlab_conditions` | Top detected condition (e.g., Nitrogen Deficiency). A weak candidate reads `Suspected: Nitrogen Deficiency` |
| `sensor.plantlab_pests` | Top detected pest (e.g., Spider Mites). A weak candidate reads `Suspected: Spider Mites` |
| `sensor.plantlab_growth_stage` | Growth stage: vegetative / flowering / seedling (cannabis only) |
| `sensor.plantlab_nutrient_analysis` | Mulder's Chart nutrient antagonism hypothesis (e.g., Potassium Excess) |
| `sensor.plantlab_likely_area` | Clinical group when the specific diagnosis is uncertain (e.g., Mobile-nutrient issue); `none` when confident |
| `binary_sensor.plantlab_problem` | On when plant is unhealthy. The `suspected` attribute is true when every listed problem is only suspected |

### Suspected conditions

When the API finds an unhealthy plant but no condition passes its threshold, it returns its best candidates with `suspected: true`. A suspected candidate is a weak, early signal. Treat it as low confidence and monitor the plant. The conditions and pests sensors put `Suspected:` before the name. Each item in their attribute lists, and each problem on the problem sensor, carries a `suspected` flag. The `suspected` attribute on each sensor is true when the top item is suspected. The problem sensor stays on, because the plant is unhealthy.

The `plantlab.diagnose` service returns the API response unchanged. The health sensor exposes the `species`, `species_confidence`, `species_name`, `in_scope`, and `routed_reason` attributes.

A tomato diagnosis shows health, conditions, and pests like a cannabis diagnosis. An unhealthy tomato can have no named cause. Then health reads `unhealthy`, the problem sensor is on, and the conditions and pests sensors read `none`. For an out-of-scope image, health reports `out_of_scope` and plant count reports zero.

## Free Tier

PlantLab's free tier gives you 3 diagnoses per day - one morning check, one evening, and a spare for when you're feeling paranoid.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
