from collections.abc import Callable
from datetime import datetime

from .circuit import DigitalstromCircuit
from .device import DigitalstromDevice
from .exceptions import ServerError


class DigitalstromChannel:
    def __init__(self, device: DigitalstromDevice, index: int | str):
        self.device = device
        self.index = index
        self.update_callbacks: list[Callable] = []
        self.last_value: float | bool | str | None = None

    def register_update_callback(self, callback: Callable) -> Callable[[], None]:
        if callback not in self.update_callbacks:
            self.update_callbacks.append(callback)

        def unregister_update_callback() -> None:
            if callback in self.update_callbacks:
                self.update_callbacks.remove(callback)

        return unregister_update_callback

    def update(
        self, state: float | bool | str | None, extra: int | dict | None = None
    ) -> None:
        self.last_value = state
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
        channel_id: str,
        channel_name: str,
        channel_type: str,
    ):
        super().__init__(device, index)
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.channel_type = channel_type
        self.prepared_value: float | None = None
        self.last_value: float | None = None

    async def get_value(self) -> float | None:
        try:
            result = await self.device.client.request(
                f"property/getFloating?path=/apartment/zones/zone{self.device.zone_id}/devices/{self.device.dsuid}/status/outputs/{self.channel_id}/targetValue"
            )
            self.last_value = result.get("value", None)
        except ServerError:
            self.last_value = None
        return self.last_value

    async def set_value(self, value: float) -> None:
        await self.device.client.request(
            f"device/setOutputChannelValue?dsuid={self.device.dsuid}&channelvalues={self.channel_id}={value}&applyNow=1"
        )

    def prepare_value(self, value: float) -> None:
        self.prepared_value = value


class DigitalstromButtonChannel(DigitalstromChannel):
    def __init__(self, device: DigitalstromDevice):
        super().__init__(device, 0)
        self.bus_event_received: datetime | None = None


class DigitalstromMeterSensorChannel(DigitalstromChannel):
    def __init__(self, circuit: DigitalstromCircuit, identifier: str):
        super().__init__(circuit, identifier)
        self.circuit = circuit

    async def get_value(self) -> float | None:
        if not self.circuit.has_metering:
            return None
        if self.index == "power":
            # Unit: Watt
            data = await self.circuit.client.request(
                f"circuit/getConsumption?id={self.circuit.dsid}"
            )
            return data.get("consumption")
        elif self.index == "energy":
            # Unit: Watt seconds
            data = await self.circuit.client.request(
                f"circuit/getEnergyMeterValue?id={self.circuit.dsid}"
            )
            return data.get("meterValue")
        return None
