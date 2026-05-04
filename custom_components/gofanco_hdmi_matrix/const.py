DOMAIN = "gofanco_hdmi_matrix"
MANUFACTURER = "Gofanco"
MODEL = "PRO-Matrix44-SC"

# Configuration keys
CONF_HOST = "host"
CONF_NAME = "name"

# Default values
DEFAULT_NAME = "Gofanco HDMI Matrix"
DEFAULT_PORT = 80
UPDATE_INTERVAL = 30  # seconds — increased from 10 to reduce connection load on device

# API endpoints
API_ENDPOINT = "/inform.cgi"

# Device info
DEVICE_INFO = {
    "identifiers": {(DOMAIN, "gofanco_4x4_matrix")},
    "manufacturer": MANUFACTURER,
    "model": MODEL,
    "name": DEFAULT_NAME,
}
