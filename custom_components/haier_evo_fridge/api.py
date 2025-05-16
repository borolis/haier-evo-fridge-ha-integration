from __future__ import annotations
import inspect
import requests
import json
import time
import threading
import uuid
import socket
from enum import Enum
from datetime import datetime, timezone, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ratelimit import limits, sleep_and_retry
from websocket import WebSocketConnectionClosedException, WebSocketException, WebSocketApp, WebSocket
from requests.exceptions import ConnectionError, Timeout, HTTPError
from urllib.parse import urlparse, urljoin, parse_qs
from urllib3.exceptions import NewConnectionError
from homeassistant.core import HomeAssistant
from homeassistant import exceptions
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode, SWING_OFF, PRESET_NONE
from .logger import _LOGGER
from . import yaml_helper
from . import const as C # noqa


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidDevicesList(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class SocketStatus(Enum):
    PRE_INITIALIZATION = 0
    INITIALIZING = 1
    INITIALIZED = 2
    NOT_INITIALIZED = 3


class Haier(object):

    def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
        self.hass: HomeAssistant = hass
        self.devices: list[HaierFridge] = []
        self._email: str = email
        self._password: str = password
        self._lock = threading.Lock()
        self._token: str | None = None
        self._tokenexpire: datetime | None = None
        self._refreshtoken: str | None = None
        self._refreshexpire: datetime | None = None
        self._socket_app = None
        self._disconnect_requested = False
        self._socket_status: SocketStatus = SocketStatus.PRE_INITIALIZATION

    @property
    def token(self) -> str | None:
        return self._token

    @property
    def load_tokens(self):
        return self._load_tokens

    def _load_tokens(self) -> None:
        try:
            filename = self.hass.config.path(C.DOMAIN)
            with open(filename, "r") as f:
                data = json.load(f)
            assert isinstance(data, dict), "Bad saved tokens file"
            self._token = data.get("token", None)
            tokenexpire = data.get("tokenexpire")
            self._tokenexpire = datetime.fromisoformat(tokenexpire) if tokenexpire else None
            self._refreshtoken = data.get("refreshtoken", None)
            refreshexpire = data.get("refreshexpire")
            self._refreshexpire = datetime.fromisoformat(refreshexpire) if refreshexpire else None
        except Exception as e:
            _LOGGER.error(f"Failed to load tokens file: {e}")
        else:
            _LOGGER.info(f"Loaded tokens file: {filename}")

    def _save_tokens(self) -> None:
        try:
            filename = self.hass.config.path(C.DOMAIN)
            with open(filename, "w") as f:
                json.dump({
                    "token": self._token,
                    "tokenexpire": str(self._tokenexpire) if self._tokenexpire else None,
                    "refreshtoken": self._refreshtoken,
                    "refreshexpire": str(self._refreshexpire) if self._refreshexpire else None,
                }, f)
        except Exception as e:
            _LOGGER.error(f"Failed to save tokens file: {e}")
        else:
            _LOGGER.info(f"Saved tokens file: {filename}")

    def _clear_tokens(self) -> None:
        self._token = None
        self._tokenexpire = None
        self._refreshtoken = None
        self._refreshexpire = None
        self._save_tokens()

    @sleep_and_retry
    @limits(calls=C.CALLS, period=C.RATE_LIMIT)
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            # Setting a default timeout for requests
            kwargs.setdefault('timeout', C.API_TIMEOUT)
            headers = kwargs.setdefault('headers', {})
            headers.setdefault('User-Agent', "curl/7.81.0")
            headers.setdefault('Accept', "*/*")
            resp = requests.request(method, url, **kwargs)
            # Handling 429 Too Many Requests with retry
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                _LOGGER.info(f"Rate limited. Retrying after {retry_after} seconds.")
                time.sleep(retry_after)
                raise HTTPError("429 Too Many Requests")
            # Raise for other HTTP errors
            resp.raise_for_status()
            return resp
        except (ConnectionError, NewConnectionError, socket.gaierror) as e:
            _LOGGER.error(f"Network error occurred: {e}. Retrying...")
            raise e  # Re-raise to allow retry mechanisms to handle this
        except Timeout as e:
            _LOGGER.error(f"Request timed out: {e}. Retrying...")
            raise e
        except HTTPError as e:
            _LOGGER.error(f"HTTP error occurred: {e}. Retrying...")
            raise e

    @retry(
        retry=retry_if_exception_type(requests.exceptions.HTTPError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def login(self, refresh: bool = False) -> None:
        if refresh and self._refreshtoken: # token refresh
            refresh_path = urljoin(C.API_PATH, C.API_TOKEN_REFRESH)
            _LOGGER.info(f"Refreshing token in to {refresh_path} with email {self._email}")
            resp = self.make_request('POST', refresh_path, data={'refreshToken': self._refreshtoken})
            _LOGGER.info(f"Refresh ({self._email}) status code: {resp.status_code}")
        else:  # initial login
            login_path = urljoin(C.API_PATH, C.API_LOGIN)
            _LOGGER.info(f"Logging in to {login_path} with email {self._email}")
            resp = self.make_request('POST', login_path, data={'email': self._email, 'password': self._password})
            _LOGGER.info(f"Login ({self._email}) status code: {resp.status_code}")
        try:
            assert resp, "No response from login"
            assert resp.status_code == 200, f"Status code is not 200 {resp.status_code}"
            assert "application/json" in resp.headers.get("content-type"), f"Bad content type"
            data = resp.json()
            _LOGGER.debug(f"{data}")
            assert "data" in data, f"Bad json, data not found"
            error = data.get("error")
            if error is not None:
                self._clear_tokens()
                raise AssertionError(f"Error {error}")
            data = data["data"]
            assert isinstance(data, dict), f"Data is not dict: {data}"
            assert "token" in data, f"Bad data, token not found"
            token = data["token"]
            assert isinstance(token, dict), f"Token is not dict: {token}"
            assert "accessToken" in token, f"Bad token data, accessToken not found"
            assert "refreshToken" in token, f"Bad token data, refreshToken not found"
            self._token = token.get("accessToken")
            self._tokenexpire = datetime.strptime(token.get("expire"), "%Y-%m-%dT%H:%M:%S%z")
            self._refreshtoken = token.get("refreshToken")
            self._refreshexpire = datetime.strptime(token.get("refreshExpire"), "%Y-%m-%dT%H:%M:%S%z")
            _LOGGER.info(
                f"Successful refreshed token for email {self._email}"
                if refresh else
                f"Successful login for email {self._email}"
            )
            self._save_tokens()
        except Exception as e:
            _LOGGER.error(
                f"Failed to login/refresh token for email {self._email}, "
                f"response was: {resp}, "
                f"err: {e}"
            )
            raise InvalidAuth()

    def auth(self) -> None:
        with self._lock:
            tzinfo = timezone(timedelta(hours=+3.0))
            # tzinfo = datetime.now(timezone.utc).astimezone().tzinfo
            now = datetime.now(tzinfo)
            tokenexpire = self._tokenexpire or now
            refreshexpire = self._refreshexpire or now
            if self._token:
                if tokenexpire > now:
                    return None
                elif self._refreshtoken and refreshexpire > now:
                    _LOGGER.info(f"Token to be refreshed")
                    return self.login(refresh=True)
            _LOGGER.info(f"Token expired or empty")
            return self.login()

    def pull_data(self) -> None:
        self.auth()
        devices_path = urljoin(C.API_PATH, C.API_DEVICES)
        _LOGGER.info(f"Getting devices, url: {devices_path}")
        resp = requests.get(devices_path, headers={
            'X-Auth-Token': self._token,
            'User-Agent': 'evo-mobile',
            'Device-Id': str(uuid.uuid4()),
            'Content-Type': 'application/json'
        }, timeout=C.API_TIMEOUT)
        if (
            resp.status_code == 200
            and "application/json" in resp.headers.get("content-type")
            and resp.json().get("data", {}).get("presentation", {}).get("layout", {}).get('scrollContainer', [])
        ):
            _LOGGER.debug(resp.text)
            data = resp.json().get("data", {})
            containers = data.get("presentation", {}).get("layout", {}).get('scrollContainer', [])
            for item in containers:
                component_id = item.get("trackingData", {}).get("component", {}).get("componentId", "")
                _LOGGER.debug(component_id)
                if (
                    item.get("contractName", "") == "deviceList"
                    and component_id == "72a6d224-cb66-4e6d-b427-2e4609252684"
                ): # check for smart devices only
                    state_data = item.get("state", {})
                    state_json = json.loads(state_data)
                    devices = state_json.get('items', [{}])
                    for d in devices:
                        # haierevo://device?deviceId=12:34:56:78:90:68&type=AC&serialNum=AAC0M1E0000000000000&uitype=AC_BASE
                        device_title = d.get('title', '') # only one device is supported
                        device_link = d.get('action', {}).get('link', '')
                        parsed_link = urlparse(device_link)
                        query_params = parse_qs(parsed_link.query)
                        device_mac = query_params.get('deviceId', [''])[0]
                        device_mac = device_mac.replace('%3A', ':')
                        device_serial = query_params.get('serialNum', [''])[0]
                        _LOGGER.info(
                            f"Received device successfully, "
                            f"device title {device_title}, "
                            f"device mac {device_mac}, "
                            f"device serial {device_serial}"
                        )
                        self.devices.append(HaierFridge(
                            haier=self,
                            device_mac=device_mac,
                            device_serial=device_serial,
                            device_title=device_title
                        ))
                    break
            if len(self.devices) > 0:
                self.connect_in_thread()
        else:
            _LOGGER.error(f"Failed to get devices, response was: {resp}")
            raise InvalidDevicesList()

    def get_device_by_id(self, id_: str) -> HaierFridge | None:
        return next(filter(lambda d: d.device_id == id_, self.devices), None)

    def _init_ws(self) -> None:
        self.auth()
        self._socket_app = WebSocketApp(
            url=urljoin(C.API_WS_PATH, self.token),
            on_message=self._on_message,
            on_open=self._on_open,
            on_ping=self._on_ping,
            on_close=self._on_close,
        )

    # noinspection PyUnusedLocal
    def _on_message(self, ws: WebSocket, message: str) -> None:
        _LOGGER.debug(f"Received WSS message: {message}")
        message_dict: dict = json.loads(message)
        message_device = message_dict.get("macAddress")
        device = self.get_device_by_id(message_device)
        if device is None:
            _LOGGER.error(f"Got a message for a device we don't know about: {message_device}")
        else:
            device.on_message(message_dict)

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _on_open(self, ws: WebSocket) -> None:
        _LOGGER.debug("Websocket opened")

    # noinspection PyUnusedLocal
    def _on_ping(self, ws: WebSocket) -> None:
        self._socket_app.sock.pong()

    # noinspection PyUnusedLocal
    def _on_close(self, ws: WebSocket, close_code: int, close_message: str) -> None:
        _LOGGER.debug(f"Socket closed. Code: {close_code}, message: {close_message}")
        self._auto_reconnect_if_needed()

    def _auto_reconnect_if_needed(self, command: str = None) -> None:
        self._socket_status = SocketStatus.NOT_INITIALIZED
        if not self._disconnect_requested:
            _LOGGER.debug(f"Automatically reconnecting on unwanted closed socket. {command}")
            self.connect_in_thread()
        else:
            _LOGGER.debug("Disconnect was explicitly requested, not attempting to reconnect")

    def connect(self) -> None:
        if self._socket_status not in [
            SocketStatus.INITIALIZED,
            SocketStatus.INITIALIZING,
        ]:
            self._socket_status = SocketStatus.INITIALIZING
            _LOGGER.debug(f"Connecting to websocket ({C.API_WS_PATH})")
            self._init_ws()
            try:
                self._socket_app.run_forever()
            except WebSocketException: # socket is already opened
                pass
        else:
            _LOGGER.info(
                f"Can not attempt socket connection because of current "
                f"socket status: {self._socket_status}"
            )

    def connect_in_thread(self) -> None:
        thread = threading.Thread(target=self.connect)
        thread.daemon = True
        thread.start()

    def send_message(self, payload: str) -> None:
        calling_method = inspect.stack()[1].function
        _LOGGER.debug(
            f"Sending message for command {calling_method}: "
            f"{payload}"
        )
        try:
            self._socket_app.send(payload)
        except WebSocketConnectionClosedException:
            self._auto_reconnect_if_needed()


class HaierFridge(object):

    def __init__(self, haier: Haier, device_mac: str, device_serial: str, device_title: str) -> None:
        self._haier = haier
        self._device_id = device_mac
        self._device_serial = device_serial
        self._device_name = device_title
        # Device information
        self.model_name = "Fridge"
        self._sw_version = None
        # Temperature sensors
        self._fridge_temperature = None
        self._freezer_temperature = None
        self._ambient_temperature = None
        # Temperature controls
        self._fridge_target_temperature = None
        self._freezer_target_temperature = None
        # Door state
        self._door_open = False
        # Modes
        self._vacation_mode = False
        self._super_cool_mode = False
        # Get initial status
        self._get_status()

    @property
    def hass(self) -> HomeAssistant:
        return self._haier.hass

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def device_mac(self) -> str:
        return self._device_id

    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def sw_version(self) -> str:
        return self._sw_version

    @property
    def unique_id(self) -> str:
        """Return unique ID for this device."""
        return f"haier_evo_fridge_{self._device_id}"

    # Temperature sensors
    @property
    def fridge_temperature(self) -> float | None:
        return self._fridge_temperature

    @property
    def freezer_temperature(self) -> float | None:
        return self._freezer_temperature

    @property
    def ambient_temperature(self) -> float | None:
        return self._ambient_temperature

    # Temperature controls
    @property
    def fridge_target_temperature(self) -> float | None:
        return self._fridge_target_temperature

    @property
    def freezer_target_temperature(self) -> float | None:
        return self._freezer_target_temperature

    # Door state
    @property
    def door_open(self) -> bool:
        return self._door_open

    # Modes
    @property
    def vacation_mode(self) -> bool:
        return self._vacation_mode

    @property
    def super_cool_mode(self) -> bool:
        return self._super_cool_mode

    def write_ha_state(self) -> None:
        """Write the state to Home Assistant."""
        self.hass.async_create_task(self._haier.connect())

    async def update(self) -> None:
        """Update the device state."""
        await self.hass.async_add_executor_job(self._get_status)

    def on_message(self, message_dict: dict) -> None:
        message_type = message_dict.get("event", "")
        if message_type == "status":
            self._handle_status_update(message_dict)
        elif message_type == "command_response":
            pass
        elif message_type == "info":
            pass
        elif message_type == "deviceStatusEvent":
            self._handle_device_status_update(message_dict)
        else:
            _LOGGER.warning(f"Got unknown message: {message_dict}")

    def _set_attribute(self, key, value) -> None:
        """Set device attribute value."""
        try:
            if key == C.ATTR_FRIDGE_DOOR:  # Door state
                self._door_open = value == "1"
            elif key == C.ATTR_AMBIENT_TEMP:  # Ambient temperature
                self._ambient_temperature = float(value)
            elif key == C.ATTR_FREEZER_TEMP:  # Freezer temperature
                self._freezer_temperature = float(value)
            elif key == C.ATTR_FRIDGE_TEMP:  # Fridge temperature
                self._fridge_temperature = float(value)
                self._fridge_target_temperature = float(value)
            elif key == C.ATTR_FREEZER_CONTROL:  # Freezer temperature control
                self._freezer_target_temperature = float(value)
            elif key == C.ATTR_VACATION_MODE:  # Vacation mode
                self._vacation_mode = value == "1"
            elif key == C.ATTR_SUPER_COOL:  # Super cooling mode
                self._super_cool_mode = value == "1"
        except (ValueError, TypeError) as e:
            _LOGGER.error(f"Error setting attribute {key}={value}: {e}")

    def _get_status(self):
        """Get initial device status."""
        status_url = C.API_STATUS.replace("{mac}", self.device_id)
        _LOGGER.info(f"Getting initial status of device {self.device_id}, url: {status_url}")
        resp = requests.get(status_url, headers={"X-Auth-token": self._haier.token}, timeout=C.API_TIMEOUT)
        if resp.status_code == 200:
            _LOGGER.info(f"Update device {self.device_id} status code: {resp.status_code}")
            _LOGGER.debug(resp.text)
            
            # Get device info
            device_info = resp.json().get("info", {})
            device_model = device_info.get("model", "Fridge")
            _LOGGER.info(f"Device model {device_model}")
            self.model_name = device_model
            
            # Read config values
            self._config = yaml_helper.DeviceConfig(device_model)
            
            # Get firmware version
            settings = resp.json().get("settings", {})
            self._sw_version = settings.get('firmware', {}).get('value')
            
            # Process attributes
            attributes = resp.json().get("attributes", [])
            for attr in attributes:
                key = attr.get('name', '')
                value = attr.get('currentValue')
                self._set_attribute(key, value)
            
            _LOGGER.info(
                f"Device status: "
                f"fridge_temp={self._fridge_temperature}, "
                f"freezer_temp={self._freezer_temperature}, "
                f"ambient_temp={self._ambient_temperature}, "
                f"door_open={self._door_open}, "
                f"vacation_mode={self._vacation_mode}, "
                f"super_cool={self._super_cool_mode}"
            )
            
        self.write_ha_state()

    def _handle_status_update(self, received_message: dict) -> None:
        """Handle status update from websocket."""
        message_statuses = received_message.get("payload", {}).get("statuses", [{}])
        _LOGGER.debug(
            f"Received websocket message for device {self.device_id}:\n"
            f"Full message: {received_message}\n"
            f"Status payload: {message_statuses}\n"
            f"Properties: {message_statuses[0].get('properties', {})}"
        )
        
        for key, value in message_statuses[0].get('properties', {}).items():
            _LOGGER.debug(f"Setting attribute {key} = {value}")
            self._set_attribute(key, value)
        self.write_ha_state()

    def _handle_device_status_update(self, received_message: dict) -> None:
        """Handle device status update from websocket."""
        _LOGGER.info(f"Received device status update {self.device_id} {received_message}")
        self.write_ha_state()

    async def async_set_fridge_temperature(self, temperature: int) -> None:
        """Set fridge temperature."""
        self._send_command({
            "id": self._config.get_id_by_name('fridge_temperature'),
            "value": str(temperature)
        })
        self._fridge_target_temperature = float(temperature)

    async def async_set_freezer_temperature(self, temperature: int) -> None:
        """Set freezer temperature."""
        self._send_command({
            "id": self._config.get_id_by_name('freezer_temperature'),
            "value": str(temperature)
        })
        self._freezer_target_temperature = float(temperature)

    async def async_set_vacation_mode(self, enabled: bool) -> None:
        """Set vacation mode."""
        self._send_command({
            "id": self._config.get_id_by_name('vacation_mode'),
            "value": "1" if enabled else "0"
        })
        self._vacation_mode = enabled

    async def async_set_super_cool_mode(self, enabled: bool) -> None:
        """Set super cool mode."""
        self._send_command({
            "id": self._config.get_id_by_name('super_cool'),
            "value": "1" if enabled else "0"
        })
        self._super_cool_mode = enabled

    async def async_set_super_freeze_mode(self, enabled: bool) -> None:
        """Set super freeze mode."""
        self._send_command({
            "id": self._config.get_id_by_name('super_freeze'),
            "value": "1" if enabled else "0"
        })
        self._super_freeze_mode = enabled

    def _send_command(self, command: dict) -> None:
        """Send command to device."""
        import uuid
        
        trace_id = str(uuid.uuid4())
        message = {
            "action": "command",
            "macAddress": self.device_id,
            "command": {
                "commandName": command["id"],
                "value": command["value"]
            },
            "trace": trace_id
        }
        
        _LOGGER.debug(
            f"Sending command to device {self.device_id}:\n"
            f"Command: {command}\n"
            f"Message: {message}\n"
            f"Trace ID: {trace_id}"
        )
        
        self._haier.send_message(json.dumps(message))
