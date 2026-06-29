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
        # New API
        self.target_value: float | None = None
        self.initial_value: float | None = None
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

    async def get_value(self) -> float | None:
        # Old API
        try:
            result = await self.device.client.request(
                f"property/getFloating?path=/apartment/zones/zone{self.device.zone_id}/devices/{self.device.dsuid}/status/outputs/{self.channel_id}/targetValue"
            )
            self.last_value = result.get("value", None)
        except ServerError:
            self.last_value = None
        return self.last_value

    def value(self) -> float | None:
        # New API
        if self.target_value is not None:
            if (
                self.initial_value is not None
                and self.start_time is not None
                and self.end_time is not None
            ):
                now = datetime.now()
                if now >= self.end_time:
                    return self.target_value
                if now <= self.start_time:
                    return self.initial_value
                ratio = (now - self.start_time).total_seconds() / (
                    self.end_time - self.start_time
                ).total_seconds()
                return (
                    self.initial_value
                    + (self.target_value - self.initial_value) * ratio
                )
            else:
                return self.target_value
        return None

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


class DigitalstromMeterSensorChannel:
    def __init__(self, circuit: DigitalstromCircuit, identifier: str):
        self.circuit = circuit
        self.index = identifier

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
