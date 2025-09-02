import logging
import time

from .client import DigitalstromClient
from .const import BUTTON_BUS_EVENT_TIMEOUT

APARTMENT_SCENES: list = [
    ("Auto Standby", 64, None, None, None),
    ("Standby", 67, None, None, None),
    ("Deep Off", 68, None, None, None),
    ("Zone Active", 75, None, None, None),
    ("Sleeping", 69, 70, "hibernation", "sleeping"),
    ("Absent", 72, 71, "presence", "absent"),
    ("Door Bell", 73, None, None, None),
    ("Burglary", 93, None, None, None),
    ("Panic", 65, None, "panic", "active"),
    ("Fire", 76, None, "fire", "active"),
    ("Alarm 1", 74, None, "alarm", "active"),
    ("Alarm 2", 83, None, "alarm2", "active"),
    ("Alarm 3", 84, None, "alarm3", "active"),
    ("Alarm 4", 85, None, "alarm4", "active"),
    ("Wind", 86, 87, "wind", "active"),
    ("Rain", 88, 89, "rain", "active"),
    ("Hail", 90, 91, "hail", "active"),
    ("Pollution", 92, None, None, None),
]


class DigitalstromApartment:
    def __init__(self, client: DigitalstromClient, system_dsuid: str):
        self.client = client
        self.dsuid = system_dsuid
        self.devices = {}
        self.circuits = {}
        self.zones = {}
        self.scenes = []
        self.logger = logging.getLogger("digitalstrom_api")
        client.register_event_callback(self.event_callback)
        from .scene import DigitalstromApartmentScene

        for scene in APARTMENT_SCENES:
            scene_name, call_number, undo_number, state_name, on_state = scene
            self.scenes.append(
                DigitalstromApartmentScene(
                    self, scene_name, call_number, undo_number, state_name, on_state
                )
            )

    async def call_scene(self, scene: int, force: bool = False) -> None:
        force_str = "&force=true" if force else ""
        await self.client.request(f"apartment/callScene?sceneNumber={scene}{force_str}")

    async def undo_scene(self, scene: int) -> None:
        await self.client.request(f"apartment/undoScene?sceneNumber={scene}")

    def find_split_devices(self) -> None:
        devices = sorted(self.devices.values(), key=lambda x: int(x.dsuid, 16))
        for prev, curr in zip(devices, devices[1:]):
            if (
                int(curr.dsuid, 16) <= int(prev.dsuid, 16) + 0x100
                and prev.meter_dsuid == curr.meter_dsuid
                and (
                    curr.dsuid_index != 0
                    or (curr.oem_part_number not in [0, 1])
                    or not (
                        prev.dsuid_index == curr.dsuid_index
                        and prev.oem_part_number == curr.oem_part_number
                    )
                )
            ):
                parent_device = (
                    prev if prev.parent_device is None else prev.parent_device
                )
                curr.parent_device = parent_device
                self.logger.debug(f"Merging devices {parent_device.dsuid} {curr.dsuid}")

    async def get_devices(self) -> dict:
        data = await self.client.request("apartment/getDevices")
        self.logger.debug(f"getDevices {data}")
        for d in data:
            if (dsuid := d.get("dSUID")) and (len(dsuid) > 0):
                if dsuid not in self.devices.keys():
                    from .device import DigitalstromDevice

                    device = DigitalstromDevice(self.client, self, dsuid)
                    self.devices[dsuid] = device
                self.devices[dsuid].load_from_dict(d)
        self.find_split_devices()
        return self.devices

    async def get_circuits(self) -> dict:
        data = await self.client.request("apartment/getCircuits")
        self.logger.debug(f"getCircuits {data}")
        if circuits := data.get("circuits"):
            for d in circuits:
                if (dsuid := d.get("dSUID")) and (len(dsuid) > 0):
                    if dsuid not in self.circuits.keys():
                        from .circuit import DigitalstromCircuit

                        circuit = DigitalstromCircuit(self.client, self, dsuid)
                        self.circuits[dsuid] = circuit
                    self.circuits[dsuid].load_from_dict(d)
        return self.circuits

    async def get_zones(self) -> dict:
        data = await self.client.request("apartment/getReachableGroups")
        self.logger.debug(f"getReachableGroups {data}")
        if zones := data.get("zones"):
            for z in zones:
                if "zoneID" in z:
                    zone_id = int(z["zoneID"])
                    if zone_id not in self.zones.keys():
                        from .zone import DigitalstromZone

                        zone = DigitalstromZone(self.client, self, zone_id)
                        self.zones[zone_id] = zone
                    self.zones[zone_id].load_from_dict(z)
                    await zone.get_scenes()
        await self.get_zone_climate_data()
        return self.zones

    async def get_zone_climate_data(self) -> None:
        data = await self.client.request("apartment/getTemperatureControlStatus")
        if zones := data.get("zones"):
            self.logger.debug(f"getTemperatureControlStatus {data}")
            for z in zones:
                if "id" in z:
                    zone_id = int(z["id"])
                    if zone_id in self.zones.keys():
                        self.zones[zone_id].load_climate_data_from_dict(z)

    async def event_callback(self, data: dict) -> None:
        if name := data.get("name"):
            self.logger.debug(f"event {data}")
            if name == "deviceSensorValue":
                dsuid = data["source"]["dsid"]
                index = int(data["properties"]["sensorIndex"])
                # sensor_type = int(data["properties"]["sensorType"])
                # raw_value = int(data["properties"]["sensorValue"])  # "sensorValue" is not always present
                value = float(data["properties"]["sensorValueFloat"])
                if sensor := self.devices.get(dsuid).sensors.get(index):
                    sensor.update(value)
            elif name == "deviceBinaryInputEvent":
                dsuid = data["source"]["dsid"]
                index = int(data["properties"]["inputIndex"])
                raw_state = int(data["properties"]["inputState"])
                state = raw_state > 0
                # input_type = int(data["properties"]["inputType"])
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
                # raw_value = data["properties"]["value"]
                # statename = data["properties"]["statename"]

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

            elif name in ["callScene", "callSceneBus"]:
                dsuid = data["properties"].get(
                    "originDSUID", data["source"].get("dsid", None)
                )
                if (device := self.devices.get(dsuid)) and (device.button is not None):
                    if name == "callSceneBus":
                        device.button.bus_event_received = time.time()
                    elif (device.button.bus_event_received is not None) and (
                        device.button.bus_event_received
                        > time.time() - BUTTON_BUS_EVENT_TIMEOUT
                    ):
                        self.logger.debug(f"Ignoring repeated event")
                        return
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
            elif name == "apartmentProxyStateChanged":
                # TODO: Update all output channels
                pass
