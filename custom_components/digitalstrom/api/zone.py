from .apartment import DigitalstromApartment
from .client import DigitalstromClient


class DigitalstromZone:
    def __init__(
        self, client: DigitalstromClient, apartment: DigitalstromApartment, zone_id: int
    ):
        from .scene import DigitalstromZoneScene

        self.client = client
        self.zone_id = zone_id
        self.apartment = apartment
        self.name = ""
        self.group_ids: list[int] = []
        self.scenes: dict[str, DigitalstromZoneScene] = {}
        self.climate_control_mode: int | None = None
        self.climate_control_state: int | None = None
        self.climate_operation_mode: int | None = None
        self.current_temperature: float | None = None
        self.target_temperature: float | None = None
        self.control_value: float | None = None

    async def call_scene(
        self, scene: int, group_id: int | None = None, force: bool = False
    ) -> None:
        group_str = "" if group_id is None else f"&groupID={group_id}"
        force_str = "&force=true" if force else ""
        await self.client.request(
            f"zone/callScene?id={self.zone_id}&sceneNumber={scene}{group_str}{force_str}"
        )

    async def undo_scene(self, scene: int, group_id: int | None = None) -> None:
        group_str = "" if group_id is None else f"&groupID={group_id}"
        await self.client.request(
            f"zone/undoScene?id={self.zone_id}&sceneNumber={scene}{group_str}"
        )

    async def set_target_temperature(
        self, target_temperature: float, operation_mode: int | None = None
    ) -> None:
        if operation_mode is None:
            operation_mode = self.climate_operation_mode
        await self.client.request(
            f'zone/setTemperatureControlConfig2?id={self.zone_id}&targetTemperatures={{"{operation_mode}": {target_temperature}}}'
        )

    def load_from_dict(self, data: dict) -> None:
        if "zoneID" in data:
            zone_id = int(data["zoneID"])
            if zone_id == self.zone_id:
                if (name := data.get("name")) and (len(name) > 0):
                    self.name = name
                if (group_ids := data.get("groups")) and (len(group_ids) > 0):
                    self.group_ids = group_ids

    def load_climate_data_from_dict(self, data: dict) -> None:
        if "id" in data:
            zone_id = int(data["id"])
            if zone_id == self.zone_id:
                if (control_mode := data.get("ControlMode", None)) is not None:
                    self.climate_control_mode = int(control_mode)
                if (control_state := data.get("ControlState", None)) is not None:
                    self.climate_control_state = int(control_state)
                if (operation_mode := data.get("OperationMode", None)) is not None:
                    self.climate_operation_mode = int(operation_mode)
                if (
                    current_temperature := data.get("TemperatureValue", None)
                ) is not None:
                    self.current_temperature = float(current_temperature)
                if (target_temperature := data.get("NominalValue", None)) is not None:
                    self.target_temperature = float(target_temperature)
                if (control_value := data.get("ControlValue", None)) is not None:
                    self.control_value = float(control_value)

    async def get_scenes(self) -> None:
        from .scene import DigitalstromZoneScene

        for group_id in self.group_ids:
            result = await self.client.request(
                f"zone/getReachableScenes?id={self.zone_id}&groupID={group_id}"
            )
            reachable_scenes = result.get("reachableScenes", [])
            named_scenes = result.get("userSceneNames", [])
            for scene in named_scenes:
                if number := scene.get("sceneNr"):
                    identifier = f"{group_id}_{int(number)}"
                    if identifier not in self.scenes.keys():
                        self.scenes[identifier] = DigitalstromZoneScene(
                            self, int(number), group_id, scene.get("sceneName", None)
                        )
            for number in reachable_scenes:
                identifier = f"{group_id}_{int(number)}"
                if identifier not in self.scenes.keys():
                    self.scenes[identifier] = DigitalstromZoneScene(
                        self, int(number), group_id, None
                    )
