import re

from .apartment import DigitalstromApartment
from .client import DigitalstromClient
from .const import INVERTED_BINARY_INPUTS, NOT_DIMMABLE_OUTPUT_MODES
from .exceptions import ServerError


class DigitalstromDevice:
    def __init__(
        self, client: DigitalstromClient, apartment: DigitalstromApartment, dsuid: str
    ):
        self.client = client
        self.apartment = apartment
        self.dsuid = dsuid
        self.dsid = ""
        self.name = ""
        self.hw_info = ""
        self.oem_product_url = None
        self.manufacturer = "digitalSTROM"
        self.zone_id = None
        self.button_used = None
        self.button_group = 0
        self.output_dimmable = None
        self.sensors = {}
        self.binary_inputs = {}
        self.output_channels = {}
        self.button = None
        self.meter_dsuid = None
        self.dsuid_index = None
        self.oem_part_number = None
        self.parent_device = None
        self.available = False
        self.availability_callbacks = []
        self.reading_power_state_unsupported = False

    def availability_callback(self, available: bool, call_parent: bool = False) -> None:
        if not self.available == available:
            self.available = available
            if call_parent and (parent_device is not None):
                parent_device.availability_callback(available)
            for callback in self.availability_callbacks:
                callback(available)

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

    async def get_power_state(self) -> int:
        if self.reading_power_state_unsupported:
            return None
        try:
            result = await self.client.request(
                f"property/getFloating?path=/apartment/zones/zone{self.zone_id}/devices/{self.dsuid}/status/outputs/powerState/targetValue"
            )
            return result.get("value", None)
        except ServerError:
            self.reading_power_state_unsupported = True
        return None

    async def call_scene(self, scene: int, force: bool = False) -> None:
        force_str = "&force=true" if force else ""
        await self.client.request(
            f"device/callScene?dsuid={self.dsuid}&sceneNumber={scene}{force_str}"
        )

    async def undo_scene(self, scene: int, force: bool = False) -> None:
        force_str = "&force=true" if force else ""
        await self.client.request(
            f"device/undoScene?dsuid={self.dsuid}&sceneNumber={scene}{force_str}"
        )

    def _load_general(self, data: dict) -> None:
        if (dsid := data.get("id")) and (len(dsid) > 0):
            self.dsid = dsid
        if (name := data.get("name")) and (len(name) > 0):
            self.name = name
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
            inverted = False
            # if (input_property := data.get("AKMInputProperty")) and (
            #     input_property == "inverted"
            # ):
            #     inverted = True
            if self.hw_info in INVERTED_BINARY_INPUTS:
                inverted = True
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
        if output_mode := data.get("outputMode"):
            if output_mode == 0:
                self.output_dimmable = None
            elif output_mode in NOT_DIMMABLE_OUTPUT_MODES:
                self.output_dimmable = False
            else:
                self.output_dimmable = True
        if (
            (output_mode := data.get("outputMode"))
            and output_mode > 0
            and (output_channels := data.get("outputChannels"))
            and len(output_channels) > 0
        ):
            for output_channel in output_channels:
                index = output_channel["channelIndex"]
                channel_id = output_channel["channelId"]
                channel_name = output_channel["channelName"]
                channel_type = output_channel["channelType"]
                from .channel import DigitalstromOutputChannel

                self.output_channels[index] = DigitalstromOutputChannel(
                    self, index, channel_id, channel_name, channel_type
                )
