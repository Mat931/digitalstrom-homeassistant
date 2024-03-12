from .apartment import DigitalstromApartment
from .client import DigitalstromClient


class DigitalstromCircuit:
    def __init__(
        self, client: DigitalstromClient, apartment: DigitalstromApartment, dsuid: str
    ):
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

    def load_from_dict(self, data: dict):
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
