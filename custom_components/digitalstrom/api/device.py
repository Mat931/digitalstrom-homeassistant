import re
from collections.abc import Callable
from typing import Self

from .apartment import DigitalstromApartment
from .client import DigitalstromClient
from .const import (
    INVERTED_BINARY_INPUTS,
    NOT_DIMMABLE_OUTPUT_MODES,
    SUPPORTED_OUTPUT_CHANNELS,
)
from .exceptions import ServerError


class DigitalstromDevice:
    def __init__(
        self, client: DigitalstromClient, apartment: DigitalstromApartment, dsuid: str
    ):
        from .channel import (
            DigitalstromBinaryInputChannel,
            DigitalstromButtonChannel,
            DigitalstromOutputChannel,
            DigitalstromSensorChannel,
        )

        self.client = client
        self.apartment = apartment
        self.dsuid = dsuid
        self.dsid = ""
        self.name = ""
        self.hw_info = ""
        self.oem_product_url = None
        self.manufacturer = "digitalSTROM"
        self.zone_id: int | None = None
        self.button_used: bool | None = None
        self.button_group = 0
        self.output_dimmable: bool | None = None
        self.sensors: dict[int, DigitalstromSensorChannel] = {}
        self.binary_inputs: dict[int, DigitalstromBinaryInputChannel] = {}
        self.output_channels: dict[int, DigitalstromOutputChannel] = {}
        self.button: DigitalstromButtonChannel | None = None
        self.meter_dsuid: str | None = None
        self.dsuid_index = None
        self.oem_part_number = None
        self.parent_device: Self | None = None
        self.available = False
        self.availability_callbacks: list[Callable] = []
        self.reading_power_state_supported: bool | None = None
        self.unique_device_names: list[str] = []
        self.output_channel_log_count = 0

    def get_parent(self) -> Self:
        if self.parent_device is not None and self.parent_device != self:
            return self.parent_device.get_parent()
        return self

    def update_availability(self, available: bool) -> None:
        parent = self.get_parent()
        if parent != self:
            parent.update_availability(available)
            return
        if not self.available == available:
            self.available = available
            for callback in self.availability_callbacks:
                callback(available)

    def register_availability_callback(
        self, callback: Callable[[bool], None]
    ) -> Callable[[], None]:
        if callback not in self.availability_callbacks:
            self.availability_callbacks.append(callback)

        def unregister_availability_callback() -> None:
            if callback in self.availability_callbacks:
                self.availability_callbacks.remove(callback)

        return unregister_availability_callback

    def load_from_dict(self, data: dict) -> None:
        if (dsuid := data.get("dSUID")) and (dsuid == self.dsuid):
            self._load_general(data)
            self._load_button(data)
            self._load_sensors(data)
            self._load_binary_inputs(data)
            self._load_outputs(data)

    def output_channels_clear_prepared_values(self) -> None:
        for index in self.output_channels.keys():
            self.output_channels[index].prepared_value = None

    async def output_channels_set_prepared_values(self) -> None:
        channel_values = []
        for output_channel in self.output_channels.values():
            if output_channel.prepared_value is not None:
                channel_values.append(
                    f"{output_channel.channel_id}={output_channel.prepared_value}"
                )
        channel_values_str = ";".join(channel_values)
        await self.client.request(
            f"device/setOutputChannelValue?dsuid={self.dsuid}&channelvalues={channel_values_str}&applyNow=1"
        )

    async def output_channels_get_values(
        self, channels: list[str] | None = None
    ) -> None:
        channel_values = []
        if channels is None:
            channels = [x.channel_type for x in self.output_channels.values()]
        for output_channel_type in channels:
            if output_channel_type in SUPPORTED_OUTPUT_CHANNELS:
                channel_values.append(output_channel_type)
        channel_values_str = ";".join(channel_values)
        result_channel_values = {}

        result = await self.client.request(
            f"device/getOutputChannelValue?dsuid={self.dsuid}&channels={channel_values_str}"
        )
        if self.output_channel_log_count < 100:
            self.output_channel_log_count += 1
            self.apartment.logger.debug(
                f"device/getOutputChannelValue?dsuid={self.dsuid}&channels={channel_values_str} {result}"
            )
        if (result_channels := result.get("channels")) is not None:
            for channel in result_channels:
                channel_id = channel.get("channel")
                channel_value = channel.get("value")
                if channel_id is not None:
                    result_channel_values[channel_id] = channel_value

        for output_channel in self.output_channels.values():
            if output_channel.channel_type in channels:
                output_channel.last_value = result_channel_values.get(
                    output_channel.channel_type, None
                )

    async def get_power_state(self) -> float | None:
        if self.reading_power_state_supported == False:
            return None
        try:
            result = await self.client.request(
                f"property/getFloating?path=/apartment/zones/zone{self.zone_id}/devices/{self.dsuid}/status/outputs/powerState/targetValue"
            )
            self.reading_power_state_supported = True
            return result.get("value", None)
        except ServerError:
            if self.reading_power_state_supported is None:
                self.reading_power_state_supported = False
        return None

    async def call_scene(self, scene: int, force: bool = False) -> None:
        force_str = "&force=true" if force else ""
        await self.client.request(
            f"device/callScene?dsuid={self.dsuid}&sceneNumber={scene}{force_str}"
        )

    async def undo_scene(self, scene: int) -> None:
        await self.client.request(
            f"device/undoScene?dsuid={self.dsuid}&sceneNumber={scene}"
        )

    def _load_general(self, data: dict) -> None:
        if (dsid := data.get("id")) and (len(dsid) > 0):
            self.dsid = dsid
        if (name := data.get("name")) is not None:
            if len(name) > 0:
                self.name = name
            if len(self.unique_device_names) == 0:
                self.unique_device_names.append(self.name)
        if (hw_info := data.get("hwInfo")) and (len(hw_info) > 0):
            self.hw_info = hw_info

        if (oem_product_url := data.get("OemProductURL")) and (
            len(oem_product_url)
        ) > 0:
            self.oem_product_url = oem_product_url
            match = re.match(
                r"https?://(www\.)?(?P<domain>[a-zA-Z0-9-.]+)", oem_product_url
            )
            if (
                match
                and (domain := match.groupdict().get("domain"))
                and len(domain) > 0
            ):
                self.manufacturer = domain
            else:
                self.manufacturer = oem_product_url

        if zone_id := data.get("zoneID"):
            self.zone_id = int(zone_id)

        if meter_dsuid := data.get("meterDSUID"):
            self.meter_dsuid = meter_dsuid

        if "dSUIDIndex" in data.keys():
            self.dsuid_index = data["dSUIDIndex"]

        if "OemPartNumber" in data.keys():
            self.oem_part_number = data["OemPartNumber"]

        if "isPresent" in data.keys():
            self.available = data["isPresent"]

    def _load_button(self, data: dict) -> None:
        if button_usage := data.get("buttonUsage"):
            from .channel import DigitalstromButtonChannel

            if button_usage == "used":
                self.button_used = True
                self.button = DigitalstromButtonChannel(self)
            elif button_usage in ["auto_unused", "manual_unused"]:
                self.button_used = False
                self.button = DigitalstromButtonChannel(self)
            else:
                self.button_used = None
        if button_group := data.get("buttonGroupMembership"):
            self.button_group = int(button_group)

    def _load_sensors(self, data: dict) -> None:
        if sensors := data.get("sensors"):
            for index in range(len(sensors)):
                sensor_dict = sensors[index]
                sensor_type = sensor_dict.get("type")
                valid = bool(sensor_dict.get("valid"))
                value = sensor_dict.get("value")
                if not valid:
                    value = None
                if sensor := self.sensors.get(index):
                    sensor.update(value, valid)
                else:
                    from .channel import DigitalstromSensorChannel

                    sensor = DigitalstromSensorChannel(self, index, sensor_type, valid)
                    sensor.update(value, valid)
                    self.sensors[index] = sensor

    def _load_binary_inputs(self, data: dict) -> None:
        if binary_inputs := data.get("binaryInputs"):
            inverted = data.get("AKMInputProperty") == "inverted"
            invert_mode = INVERTED_BINARY_INPUTS.get(self.hw_info, "default")
            if invert_mode == "always_invert":
                inverted = True
            elif invert_mode == "never_invert":
                inverted = False
            for index in range(len(binary_inputs)):
                input_dict = binary_inputs[index]
                group = input_dict.get("targetGroup")
                input_type = input_dict.get("inputType")
                input_id = input_dict.get("inputId")
                raw_state = input_dict.get("state")
                state = raw_state == 1
                if binary_input := self.binary_inputs.get(index):
                    binary_input.update(state, raw_state)
                else:
                    from .channel import DigitalstromBinaryInputChannel

                    binary_input = DigitalstromBinaryInputChannel(
                        self, index, input_type, inverted
                    )
                    binary_input.update(state, raw_state)
                    self.binary_inputs[index] = binary_input

    def _load_outputs(self, data: dict) -> None:
        output_mode = data.get("outputMode")
        if output_mode is not None:
            self.output_dimmable = output_mode not in NOT_DIMMABLE_OUTPUT_MODES
            if output_mode > 0 and (output_channels := data.get("outputChannels")):
                for output_channel in output_channels:
                    index = output_channel["channelIndex"]
                    if index not in self.output_channels.keys():
                        channel_id = output_channel["channelId"]
                        channel_name = output_channel["channelName"]
                        channel_type = output_channel["channelType"]
                        from .channel import DigitalstromOutputChannel

                        self.output_channels[index] = DigitalstromOutputChannel(
                            self, index, channel_id, channel_name, channel_type
                        )
