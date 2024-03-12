from collections.abc import Callable

from .device import DigitalstromDevice
from .exceptions import ServerError


class DigitalstromChannel:
    def __init__(self, device: DigitalstromDevice, index: int):
        self.device = device
        self.index = index
        self.update_callbacks = []
        self.last_state = None

    def register_update_callback(self, callback: Callable):
        if callback not in self.update_callbacks:
            self.update_callbacks.append(callback)

        def unregister_update_callback():
            if callback in self.update_callbacks:
                self.update_callbacks.remove(callback)

        return unregister_update_callback

    def update(self, state, extra=None):
        self.last_state = state
        for callback in self.update_callbacks:
            callback(state, extra)


class DigitalstromSensorChannel(DigitalstromChannel):
    def __init__(
        self, device: DigitalstromDevice, index: int, sensor_type: int, valid: bool
    ):
        super().__init__(device, index)
        self.sensor_type = sensor_type
        self.valid = valid


class DigitalstromBinaryInputChannel(DigitalstromChannel):
    def __init__(
        self, device: DigitalstromDevice, index: int, input_type: int, inverted: bool
    ):
        super().__init__(device, index)
        self.input_type = input_type
        self.inverted = inverted


class DigitalstromOutputChannel(DigitalstromChannel):
    def __init__(
        self,
        device: DigitalstromDevice,
        index: int,
        channel_id,
        channel_name,
        channel_type,
    ):
        super().__init__(device, index)
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.channel_type = channel_type

    async def get_value(self):
        try:
            result = await self.device.client.request(
                f"property/getFloating?path=/apartment/zones/zone{self.device.zone_id}/devices/{self.device.dsuid}/status/outputs/{self.channel_id}/targetValue"
            )
            return result.get("value", None)
        except ServerError:
            return None

    async def set_value(self, value):
        await self.device.client.request(
            f"device/setOutputChannelValue?dsuid={self.device.dsuid}&channelvalues={self.channel_id}={value}&applyNow=1"
        )


class DigitalstromButton(DigitalstromChannel):
    def __init__(self, device: DigitalstromDevice):
        super().__init__(device, 0)
