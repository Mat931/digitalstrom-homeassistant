import logging
import re
from collections.abc import Callable

from .client import DigitalstromClient
from .exceptions import ServerError

INVERTED_BINARY_INPUTS = ["EnOcean single contact (D5-00-01)"]


class DigitalstromChannel:
    def __init__(self, device, index):
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
    def __init__(self, device, index, sensor_type, valid):
        super().__init__(device, index)
        self.sensor_type = sensor_type
        self.valid = valid


class DigitalstromBinaryInputChannel(DigitalstromChannel):
    def __init__(self, device, index, input_type, inverted):
        super().__init__(device, index)
        self.input_type = input_type
        self.inverted = bool(inverted)


class DigitalstromOutputChannel(DigitalstromChannel):
    def __init__(self, device, index, channel_id, channel_name, channel_type):
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
    def __init__(self, device):
        super().__init__(device, 0)


class DigitalstromDevice:
    def __init__(self, client: DigitalstromClient, apartment, dsuid: str):
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
        self.available = False
        self.output_dimmable = None
        self.sensors = {}
        self.binary_inputs = {}
        self.output_channels = {}
        self.button = None
        self.meter = None
        self.parent_device = None
        self.available = False
        self.availability_callbacks = []

    def availability_callback(self, available, call_parent=False):
        if not self.available == available:
            self.available = available
            if call_parent and (parent_device is not None):
                parent_device.availability_callback(available)
            for callback in self.availability_callbacks:
                callback(available)

    def load_from_dict(self, data):
        if (dsuid := data.get("dSUID")) and (dsuid == self.dsuid):
            self._load_general(data)
            self._load_button(data)
            self._load_sensors(data)
            self._load_binary_inputs(data)
            self._load_outputs(data)

    def _load_general(self, data):
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

        if "isPresent" in data.keys():
            self.available = data["isPresent"]

    def _load_button(self, data):
        if button_usage := data.get("buttonUsage"):
            if button_usage == "used":
                self.button_used = True
                self.button = DigitalstromButton(self)
            elif button_usage in ["auto_unused", "manual_unused"]:
                self.button_used = False
                self.button = DigitalstromButton(self)
            else:
                self.button_used = None
        if button_group := data.get("buttonGroupMembership"):
            self.button_group = int(button_group)

    def _load_sensors(self, data):
        if sensors := data.get("sensors"):
            for index in range(len(sensors)):
                sensor_dict = sensors[index]
                sensor_type = sensor_dict.get("type")
                valid = sensor_dict.get("valid")
                value = sensor_dict.get("value")
                if not valid:
                    value = None
                if sensor := self.sensors.get(index):
                    sensor.update(value, valid)
                else:
                    sensor = DigitalstromSensorChannel(self, index, sensor_type, valid)
                    sensor.update(value, valid)
                    self.sensors[index] = sensor

    def _load_binary_inputs(self, data):
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
                    binary_input = DigitalstromBinaryInputChannel(
                        self, index, input_type, inverted
                    )
                    binary_input.update(state, raw_state)
                    self.binary_inputs[index] = binary_input

    def _load_outputs(self, data):
        if output_mode := data.get("outputMode"):
            if output_mode == 0:
                self.output_dimmable = None
            elif output_mode in [16, 35, 39, 40, 41]:
                self.output_dimmable = False
            else:
                self.output_dimmable = True
        if (
            (output_mode := data.get("outputMode"))
            and output_mode > 0
            and (output_channels := data.get("outputChannels"))
            and len(output_channels) > 0
        ):
            for channel in output_channels:
                index = channel["channelIndex"]
                channel_id = channel["channelId"]
                channel_name = channel["channelName"]
                channel_type = channel["channelType"]
                self.output_channels[index] = DigitalstromOutputChannel(
                    self, index, channel_id, channel_name, channel_type
                )


class DigitalstromCircuit:
    def __init__(self, client: DigitalstromClient, apartment, dsuid: str):
        self.client = client
        self.dsuid = dsuid
        self.apartment = apartment
        self.name = ""
        self.manufacturer = "digitalSTROM"
        self.dsid = ""
        self.hw_name = ""
        self.hw_version = ""
        self.sw_version = ""
        self.available = False
        self.has_metering = False
        self.has_metering_producer = False
        self.has_blinking = False

    def load_from_dict(self, data):
        if (dsuid := data.get("dSUID")) and (dsuid == self.dsuid):
            if (name := data.get("name")) and (len(name) > 0):
                self.name = name
            if (dsid := data.get("dsid")) and (len(dsid) > 0):
                self.dsid = dsid
            if (hw_name := data.get("hwName")) and (len(hw_name) > 0):
                self.hw_name = hw_name
            if (hw_version := data.get("hwVersionString")) and (len(hw_version) > 0):
                self.hw_version = hw_version
            if (sw_version := data.get("swVersion")) and (len(sw_version) > 0):
                self.sw_version = sw_version
            if "isPresent" in data.keys():
                self.available = data["isPresent"]
            if "hasMetering" in data.keys():
                self.has_metering = data["hasMetering"]
            if "hasMeteringProducerEnabled" in data.keys():
                self.has_metering_producer = data["hasMeteringProducerEnabled"]
            if "hasBlinking" in data.keys():
                self.has_blinking = data["hasBlinking"]

    async def get_power(self):
        # Unit: Watt
        if not self.has_metering:
            return None
        data = await self.client.request(f"circuit/getConsumption?id={self.dsid}")
        return data.get("consumption")

    async def get_energy(self):
        # Unit: Watt seconds
        if not self.has_metering:
            return None
        data = await self.client.request(f"circuit/getEnergyMeterValue?id={self.dsid}")
        return data.get("meterValue")


class DigitalstromZone:
    def __init__(self, client: DigitalstromClient, apartment, zone_id: int):
        self.client = client
        self.zone_id = zone_id
        self.apartment = apartment
        self.name = ""
        self.group_ids = []

    def load_from_dict(self, data):
        if "zoneID" in data:
            zone_id = int(data["zoneID"])
            if zone_id == self.zone_id:
                if (name := data.get("name")) and (len(name) > 0):
                    self.name = name
                if (group_ids := data.get("groups")) and (len(group_ids) > 0):
                    self.group_ids = group_ids


class DigitalstromApartment:
    def __init__(self, client: DigitalstromClient, system_dsuid: str):
        self.client = client
        self.dsuid = system_dsuid
        self.devices = {}
        self.circuits = {}
        self.zones = {}
        self.logger = logging.getLogger("digitalstrom_api")
        client.register_event_callback(self.event_callback)

    def find_split_devices(self):
        devices = sorted(self.devices.values(), key=lambda x: int(x.dsuid, 16))
        for prev, curr in zip(devices, devices[1:]):
            if (
                int(curr.dsuid, 16) <= int(prev.dsuid, 16) + 0x100
                and prev.meter == curr.meter
            ):
                curr.parent_device = (
                    prev if prev.parent_device is None else prev.parent_device
                )

    async def get_devices(self):
        data = await self.client.request("apartment/getDevices")
        self.logger.debug(f"get_devices {data}")
        for d in data:
            if (dsuid := d.get("dSUID")) and (len(dsuid) > 0):
                if dsuid not in self.devices.keys():
                    device = DigitalstromDevice(self.client, self, dsuid)
                    self.devices[dsuid] = device
                self.devices[dsuid].load_from_dict(d)
        self.find_split_devices()
        return self.devices

    async def get_circuits(self):
        data = await self.client.request("apartment/getCircuits")
        if circuits := data.get("circuits"):
            for d in circuits:
                if (dsuid := d.get("dSUID")) and (len(dsuid) > 0):
                    if dsuid not in self.circuits.keys():
                        circuit = DigitalstromCircuit(self.client, self, dsuid)
                        self.circuits[dsuid] = circuit
                    self.circuits[dsuid].load_from_dict(d)
        return self.circuits

    async def get_zones(self):
        data = await self.client.request("apartment/getReachableGroups")
        if zones := data.get("zones"):
            for z in zones:
                if "zoneID" in z:
                    zone_id = int(z["zoneID"])
                    if zone_id not in self.zones.keys():
                        zone = DigitalstromZone(self.client, self, zone_id)
                        self.zones[zone_id] = zone
                    self.zones[zone_id].load_from_dict(z)
        return self.zones

    async def event_callback(self, data) -> None:
        if name := data.get("name"):
            if name == "deviceSensorValue":
                dsuid = data["source"]["dsid"]
                index = int(data["properties"]["sensorIndex"])
                sensor_type = int(data["properties"]["sensorType"])
                value = float(data["properties"]["sensorValueFloat"])
                raw_value = int(data["properties"]["sensorValue"])
                if sensor := self.devices.get(dsuid).sensors.get(index):
                    sensor.update(value)
            elif name == "deviceBinaryInputEvent":
                dsuid = data["source"]["dsid"]
                index = int(data["properties"]["inputIndex"])
                raw_state = int(data["properties"]["inputState"])
                state = raw_state > 0
                input_type = int(data["properties"]["inputType"])
                # print(f"Binary input event: {dsuid}.{index} {state}, Raw: {raw_state}")
                if binary_sensor := self.devices.get(dsuid).binary_inputs.get(index):
                    binary_sensor.update(state, raw_state)
            elif name == "stateChange":
                state = data["properties"]["state"]
                if (dsuid := data["source"].get("dSUID")) and (
                    device := self.devices.get(dsuid)
                ):
                    if state == "unknown":
                        device.availability_callback(False, call_parent=True)
                    else:
                        device.availability_callback(True)
                raw_value = data["properties"]["value"]
                statename = data["properties"]["statename"]

                # if binary_input := self.devices.get(dsuid).binary_inputs.get(index):
                #    value = int(raw_value) == 1
                #    binary_input.update(value, raw_value)
            elif name == "DeviceEvent":
                if (
                    (data["properties"]["action"] == "ready")
                    and (dsuid := data["source"].get("dsid"))
                    and (device := self.devices.get(dsuid))
                ):
                    device.availability_callback(True)

            elif name == "callScene":
                dsuid = data["properties"].get(
                    "originDSUID", data["source"].get("dsid", None)
                )
                if (device := self.devices.get(dsuid)) and (device.button is not None):
                    scene_id = data["properties"]["sceneID"]
                    if data["source"]["isDevice"]:
                        extra_data = {}
                        extra_data["scene_id"] = scene_id
                        device.button.update("call_device_scene", extra_data)
                    if (
                        (data["source"]["isGroup"])
                        and (group_id := data["source"].get("groupID"))
                        and (zone_id := data["source"].get("zoneID"))
                    ):
                        extra_data = {}
                        extra_data["scene_id"] = scene_id
                        extra_data["group_id"] = group_id
                        extra_data["zone_id"] = zone_id
                        device.button.update("call_group_scene", extra_data)
            elif name == "buttonClick":
                dsuid = data["source"]["dsid"]
                button_index = int(data["properties"]["buttonIndex"])
                if (
                    (device := self.devices.get(dsuid))
                    and (device.button is not None)
                    and (button_index == 0)
                ):
                    extra_data = {}
                    extra_data["click_type"] = int(data["properties"]["clickType"])
                    extra_data["hold_count"] = int(
                        data["properties"].get("holdCount", 0)
                    )
                    device.button.update("button", extra_data)
            elif name == "apartmentProxyDeviceTimeout":
                if (dsuid := data["source"].get("dsid")) and (
                    device := self.devices.get(dsuid)
                ):
                    for channel in device.output_channels.values():
                        channel.update("timeout")
