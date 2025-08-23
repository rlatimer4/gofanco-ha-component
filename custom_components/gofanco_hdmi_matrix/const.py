CONST_PY = '''"""Constants for Gofanco HDMI Matrix integration."""

DOMAIN = "gofanco_hdmi_matrix"
MANUFACTURER = "Gofanco"
MODEL = "4x4 HDMI Matrix"

# Configuration keys
CONF_HOST = "host"
CONF_NAME = "name"

# Default values
DEFAULT_NAME = "Gofanco HDMI Matrix"
DEFAULT_PORT = 80
UPDATE_INTERVAL = 10  # seconds

# API endpoints
API_ENDPOINT = "/inform.cgi"

# Device info
DEVICE_INFO = {
    "identifiers": {(DOMAIN, "gofanco_4x4_matrix")},
    "manufacturer": MANUFACTURER,
    "model": MODEL,
    "name": DEFAULT_NAME,
}
