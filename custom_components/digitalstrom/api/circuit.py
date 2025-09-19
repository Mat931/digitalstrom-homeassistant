from .apartment import DigitalstromApartment
from .client import DigitalstromClient
from .exceptions import ServerError


class DigitalstromCircuit:
    def __init__(
        self, client: DigitalstromClient, apartment: DigitalstromApartment, dsuid: str
    ):
        from .channel import DigitalstromMeterSensorChannel

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
        self.sensors: dict[str, DigitalstromMeterSensorChannel] = {}

    def load_from_dict(self, data: dict) -> None:
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
            if "hasBlinking" in data.keys():
                self.has_blinking = data["hasBlinking"]
            self._load_sensors(data)

    def _load_sensors(self, data: dict) -> None:
        if "hasMetering" in data.keys():
            self.has_metering = data["hasMetering"]
        if "hasMeteringProducerEnabled" in data.keys():
            self.has_metering_producer = data["hasMeteringProducerEnabled"]
        if self.has_metering:
            for identifier in ["power", "energy"]:
                if identifier not in self.sensors.keys():
                    from .channel import DigitalstromMeterSensorChannel

                    self.sensors[identifier] = DigitalstromMeterSensorChannel(
                        self, identifier
                    )

    async def update_available(self) -> str | None:
        try:
            data = await self.client.request(
                f"circuit/firmwareCheck?dsuid={self.dsuid}"
            )
            status = data.get("status")
            # if status not in ["ok", "error", "update"]:
            #    status = None
            return status
        except ServerError:
            return None

    async def install_update(self) -> None:
        status = await self.update_available()
        if status == "update":
            data = await self.client.request(
                f"circuit/firmwareUpdate?dsuid={self.dsuid}&clearsettings=false"
            )
