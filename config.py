from enum import Enum;

class ServerType(Enum):
    WIFI = 1
    STDIO = 2


# --- Configuration ---
SERVER_TYPE = ServerType.WIFI

# Wi-Fi Configuration (only used if RUN_WIFI_SERVER is True)
# IMPORTANT: Replace with your actual Wi-Fi credentials if using Wi-Fi server
# WIFI_SSID = "🌞AsaHome🏠"
# WIFI_PASSWORD = "happywifehappylife"
WIFI_SSID = "Pixel_A"
WIFI_PASSWORD = "94899604"
MCP_SERVER_PORT = 8080  # Default port for Wi-Fi server, can be changed

