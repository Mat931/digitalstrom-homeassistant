import json
import random


class Apartment:
    def __init__(self):
        self.strings = {
            "/usr/states/hibernation/state": "",
            "/usr/states/presence/state": "",
            "/usr/states/panic/state": "",
            "/usr/states/fire/state": "",
            "/usr/states/alarm/state": "",
            "/usr/states/alarm2/state": "",
            "/usr/states/alarm3/state": "",
            "/usr/states/alarm4/state": "",
            "/usr/states/wind/state": "",
            "/usr/states/rain/state": "",
            "/usr/states/hail/state": "",
        }
        self.floats = {}
        self.device_output_channels = {}

    def handle_request(self, request):
        match request.path:
            case "/json/property/getString":
                return self.get_string(request)
            case "/json/property/getFloating":
                return self.get_floating(request)
            case "/json/apartment/callScene":
                return self.call_scene(request)
            case "/json/apartment/undoScene":
                return self.undo_scene(request)
            case "/json/apartment/getDevices":
                return self.get_devices(request)
            case "/json/apartment/getCircuits":
                return self.get_circuits(request)
            case "/json/apartment/getReachableGroups":
                return self.get_reachable_groups(request)
            case "/json/apartment/getTemperatureControlStatus":
                return self.get_temperature_control_status(request)
            case "/json/zone/getReachableScenes":
                return self.get_reachable_scenes(request)
            case "/json/circuit/getConsumption":
                return self.get_consumption(request)
            case "/json/circuit/getEnergyMeterValue":
                return self.get_energy_meter_value(request)
            case "/json/circuit/firmwareCheck":
                return self.firmware_check(request)
            case "/json/circuit/firmwareUpdate":
                return self.firmware_update(request)
            case "/json/device/getOutputChannelValue":
                return self.get_output_channel_value(request)
            case "/json/device/setOutputChannelValue":
                return self.set_output_channel_value(request)

        return {"ok": True, "result": {}}

    def get_string(self, request):
        path = request.query.get("path")
        return {"ok": True, "result": {"value": self.strings.get(path, "")}}

    def get_floating(self, request):
        path = request.query.get("path")
        return {"ok": True, "result": {"value": 0.0}}

    def call_scene(self, request):
        scene_number = request.query.get("sceneNumber")
        match int(scene_number):
            case 69:
                self.strings["/usr/states/hibernation/state"] = "sleeping"
            case 70:
                self.strings["/usr/states/hibernation/state"] = "awake"
            case 72:
                self.strings["/usr/states/presence/state"] = "absent"
            case 71:
                self.strings["/usr/states/presence/state"] = "present"

        return {"ok": True, "result": {}}

    def undo_scene(self, request):
        scene_number = request.query.get("sceneNumber")
        return {"ok": True, "result": {}}

    def get_circuits(self, request):
        data = self.read_json_file("getCircuits")
        if data is None:
            data = {"ok": True, "result": {}}
        return data

    def get_devices(self, request):
        data = self.read_json_file("getDevices")
        if data is None:
            data = {"ok": True, "result": {}}
        return data

    def get_reachable_groups(self, request):
        data = self.read_json_file("getReachableGroups")
        if data is None:
            data = {"ok": True, "result": {}}
        return data

    def get_temperature_control_status(self, request):
        data = self.read_json_file("getTemperatureControlStatus")
        if data is None:
            data = {"ok": True, "result": {}}
        return data

    def get_reachable_scenes(self, request):
        zone_id = int(request.query.get("id"))
        group_id = int(request.query.get("groupID"))
        data = self.read_json_file(
            f"getReachableScenes?id={zone_id}&groupID={group_id}"
        )
        if data is None:
            data = {"ok": True, "result": {}}
        return data

    def firmware_check(self, request):
        try:
            dsuid = request.query.get("dsuid")
            data = self.read_json_file("getCircuits")
            circuits = data.get("result").get("circuits")
            for c in circuits:
                if c.get("dSUID") == dsuid:
                    up_to_date = c.get("isUpToDate")
                    status = (
                        "ok"
                        if up_to_date
                        else ("error" if up_to_date is None else "update")
                    )
                    return {"ok": True, "status": status}
        except Exception as e:
            print(e)
        return {"ok": True, "status": "error"}

    def firmware_update(self, request):
        return {"ok": True}

    def get_consumption(self, request):
        return {"ok": True, "result": {"consumption": random.uniform(10, 100)}}

    def get_energy_meter_value(self, request):
        return {"ok": True, "result": {"meterValue": 3600000}}

    def get_output_channel_value(self, request):
        dsuid = request.query.get("dsuid")
        channels = request.query.get("channels").split(";")
        result_channels = []
        if (cv := self.device_output_channels.get(dsuid)) is not None:
            for channel in channels:
                value = cv.get(channel)
                result_channels.append({"channel": channel, "value": value})
        return {"ok": True, "result": {"channels": result_channels}}

    def set_output_channel_value(self, request):
        dsuid = request.query.get("dsuid")
        channelvalues = request.query.get("channelvalues").split(";")
        if dsuid not in self.device_output_channels:
            self.device_output_channels[dsuid] = {}
        for cv in channelvalues:
            channel, value = cv.split("=")
            value = float(value)
            self.device_output_channels[dsuid][channel] = value
        return {"ok": True, "result": {}}

    def read_json_file(self, filename):
        file_path = f"json/{filename}.json"
        try:
            with open(file_path, "rb") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            print(f"Warning: JSON file '{file_path}' does not exist")
        return None
