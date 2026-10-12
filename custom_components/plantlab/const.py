import json
from pathlib import Path

from homeassistant.const import ATTR_ENTITY_ID  # noqa: F401

DOMAIN = "plantlab"

CONF_API_KEY = "api_key"
CONF_HOST = "host"

DEFAULT_HOST = "https://api.plantlab.ai"
DEFAULT_TIMEOUT = 30

INTEGRATION_VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
USER_AGENT = f"PlantLab-HomeAssistant/{INTEGRATION_VERSION}"

SERVICE_DIAGNOSE = "diagnose"

ATTR_IMAGE_PATH = "image_path"
