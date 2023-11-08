"""
Add support for the Xiaomi Gateway Radio.
"""

import logging
import voluptuous as vol
import asyncio
from functools import partial

import homeassistant.helpers.config_validation as cv 
from homeassistant.components.media_player import (MediaPlayerEntity, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (SUPPORT_TURN_ON, SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_STEP, SUPPORT_VOLUME_SET, SUPPORT_NEXT_TRACK) 
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_TOKEN, STATE_OFF, STATE_ON)

REQUIREMENTS = ['python-miio>=0.3.7']

ATTR_MODEL = 'model'
ATTR_FIRMWARE_VERSION = 'firmware_version'
ATTR_HARDWARE_VERSION = 'hardware_version'

DEFAULT_NAME = "Xiaomi Gateway Radio"
DATA_KEY = 'media_player.xiaomi_gateway_radio'

ATTR_STATE_PROPERTY = 'state_property'
ATTR_STATE_VALUE = 'state_value'

_LOGGER = logging.getLogger(__name__)

SUPPORT_XIAOMI_GATEWAY_FM = SUPPORT_VOLUME_STEP | SUPPORT_TURN_ON | \
                    SUPPORT_TURN_OFF | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | SUPPORT_NEXT_TRACK

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Xiaomi Gateway miio platform."""
    from miio import Device, DeviceException
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config.get(CONF_HOST)
    token = config.get(CONF_TOKEN)

    _LOGGER.info("Initializing Xiaomi Gateway with host %s (token %s...)", host, token[:5])

    try:
        miio_device = Device(host, token)
        device_info = miio_device.info()
        model = device_info.model
        _LOGGER.info("%s %s %s detected",
                     model,
                     device_info.firmware_version,
                     device_info.hardware_version)

        device = XiaomiGateway(miio_device, config, device_info)
    except DeviceException:
        raise PlatformNotReady

    hass.data[DATA_KEY][host] = device
    async_add_devices([device], update_before_add=True)

class XiaomiGateway(MediaPlayerEntity):
    """Represent the Xiaomi Gateway for Home Assistant."""

    def __init__(self, device, config, device_info):
        """Initialize the entity."""
        self._device = device

        self._name = config.get(CONF_NAME)
        self._skip_update = False

        self._model = device_info.model
        self._unique_id = "{}-{}-{}".format(device_info.model,
                                            device_info.mac_address,
                                            'pause')
        self._icon = 'mdi:radio'
        self._muted = False
        self._volume = 0
        self._available = None
        self._state = None
        self._state_attrs = {
            ATTR_MODEL: self._model,
            ATTR_FIRMWARE_VERSION: device_info.firmware_version,
            ATTR_HARDWARE_VERSION: device_info.hardware_version,
            ATTR_STATE_PROPERTY: 'pause'
        }

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a device command handling error messages."""
        from miio import DeviceException
        try:
            result = await self.hass.async_add_job(
                partial(func, *args, **kwargs))

            _LOGGER.info("Response received from Gateway: %s", result)

            return result[0] == "ok"
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

    @property
    def name(self):
        """Return the display name of this Gateway."""
        return self._name

    @property
    def state(self):
        """Return _state variable, containing the appropriate constant."""
        return self._state

    @property
    def assumed_state(self):
        """Indicate that state is assumed."""
        return True

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_XIAOMI_GATEWAY_FM

    async def turn_off(self):
        result = await self._try_command(
            "Turning the Gateway off failed.", self._device.send,
            'play_fm', ['off'])

    async def turn_on(self):
        """Wake the Gateway back up from sleep."""
        result = await self._try_command(
            "Turning the Gateway on failed.", self._device.send,
            'play_fm', ['on'])

    async def volume_up(self):
        """Increase volume by one."""
        volume = round(self._volume * 100) + 1
        result = await self._try_command(
            "Turning the Gateway volume failed.", self._device.send,
            'set_fm_volume', [volume])

    async def media_next_track(self):
        """Send next track command."""
        result = await self._try_command(
            "Turning the Gateway volume failed.", self._device.send,
            'play_fm', ['next'])

    async def volume_down(self):
        """Decrease volume by one."""
        volume = round(self._volume * 100) - 1
        result = await self._try_command(
            "Turning the Gateway volume failed.", self._device.send,
            'set_fm_volume', [volume])

    async def set_volume_level(self, volume):
        volset = round(volume * 100)
        result = await self._try_command(
            "Setting the Gateway volume failed.", self._device.send,
            'set_fm_volume', [volset])

    async def mute_volume(self, mute):
        """Send mute command."""
        volume = 10
        if self._muted == False:
            volume = 0

        result = await self._try_command(
            "Turning the Gateway volume failed.", self._device.send,
            'set_fm_volume', [volume])
        if result:
            if volume == 0:
                self._muted = True
            else:
                self._muted = False

    async def async_update(self):
        """Fetch state from Gateway."""
        from miio import DeviceException

        try:
            state = await self.hass.async_add_job(
                self._device.send, 'get_prop_fm', '')
            _LOGGER.info("Got new state: %s", state)
            volume = state.pop('current_volume')
            state = state.pop('current_status')

            _LOGGER.debug("Got new state: %s", state)

            self._available = True
            if volume == 0:
                self._muted = True
            else:
                self._muted = False

            if state == 'pause':
                self._state = STATE_OFF
            elif state == 'run':
                self._state = STATE_ON
                self._volume = volume / 100
            else:
                _LOGGER.warning(
                    "New state (%s) doesn't match expected values: %s/%s",
                    state, 'pause', 'run')
                self._state = None

            self._state_attrs.update({
                ATTR_STATE_VALUE: state
            })

        except DeviceException as ex:
            self._available = False
            _LOGGER.error("Got exception while fetching the state: %s", ex)
