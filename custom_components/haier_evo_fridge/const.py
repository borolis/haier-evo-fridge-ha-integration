DOMAIN = "haier_evo_fridge"
CALLS = 5
RATE_LIMIT = 60
API_TIMEOUT = 15
API_PATH = "https://evo.haieronline.ru"
API_LOGIN = "v1/users/auth/sign-in"
API_TOKEN_REFRESH = "v1/users/auth/refresh"
API_DEVICES = "v2/ru/pages/sduiRawPaginated/smartHome?part=1&partitionWeight=6"
API_STATUS = "https://iot-platform.evo.haieronline.ru/mobile-backend-service/api/v1/config/{mac}?type=DETAILED"
API_WS_PATH = "wss://iot-platform.evo.haieronline.ru/gateway-ws-service/ws/"

# Fridge attributes
ATTR_FRIDGE_DOOR = "10"  # Door state sensor
ATTR_AMBIENT_TEMP = "2"  # Ambient temperature
ATTR_FREEZER_TEMP = "1"  # Freezer temperature
ATTR_FRIDGE_TEMP = "3"   # Fridge temperature control
ATTR_FREEZER_CONTROL = "4"  # Freezer temperature control
ATTR_VACATION_MODE = "8"  # Vacation mode
ATTR_SUPER_COOL = "6"    # Super cooling mode
ATTR_SUPER_FREEZE = "7"  # Super freeze mode

# Temperature ranges
MIN_FRIDGE_TEMP = 1
MAX_FRIDGE_TEMP = 9
MIN_FREEZER_TEMP = -24
MAX_FREEZER_TEMP = -16
