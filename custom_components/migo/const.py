"""Constants for the Saunier Duval MiGo integration."""

DOMAIN = "migo"

# Netatmo white-label credentials extracted from MiGo APK
MIGO_CLIENT_ID = "na_client_android_sdbg"
MIGO_CLIENT_SECRET = "28d36edf4ff395256555b2925688ffeb"
MIGO_USER_PREFIX = "sdbg"
MIGO_USER_AGENT = "MiGo/3.4.0 (Android)"

# API base URL
BASE_URL = "https://app.netatmo.net"

# Config entry keys
CONF_HOME_ID = "home_id"
CONF_HOME_NAME = "home_name"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"

# Polling interval — configurable via the integration options UI
CONF_SCAN_INTERVAL = "scan_interval"       # key stored in entry.options
DEFAULT_SCAN_INTERVAL_MINUTES = 60         # default: 1 hour
MIN_SCAN_INTERVAL_MINUTES = 5             # floor to avoid API bans
SCAN_INTERVAL_SECONDS = DEFAULT_SCAN_INTERVAL_MINUTES * 60  # legacy fallback

# Netatmo thermostat modes
THERM_MODE_SCHEDULE = "schedule"  # Home / following programmed schedule
THERM_MODE_AWAY = "away"          # Away / ausente
THERM_MODE_FROST_GUARD = "hg"     # Frost guard / anti-hielo
