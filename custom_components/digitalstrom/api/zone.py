from .apartment import DigitalstromApartment
from .client import DigitalstromClient


class DigitalstromZone:
    def __init__(
        self, client: DigitalstromClient, apartment: DigitalstromApartment, zone_id: int
    ):
        self.client = client
        self.zone_id = zone_id
        self.apartment = apartment
        self.name = ""
        self.group_ids = []
        self.scenes = {}

    async def call_scene(self, scene: int, group_id: int = None) -> None:
        if group_id is not None:
            await self.client.request(
                f"zone/callScene?id={self.zone_id}&sceneNumber={scene}&groupID={group_id}"
            )
        else:
            await self.client.request(
                f"zone/callScene?id={self.zone_id}&sceneNumber={scene}"
            )

    async def undo_scene(self, scene: int, group_id: int = None) -> None:
        if group_id is not None:
            await self.client.request(
                f"zone/undoScene?id={self.zone_id}&sceneNumber={scene}&groupID={group_id}"
            )
        else:
            await self.client.request(
                f"zone/undoScene?id={self.zone_id}&sceneNumber={scene}"
            )

    def load_from_dict(self, data: dict) -> None:
        if "zoneID" in data:
            zone_id = int(data["zoneID"])
            if zone_id == self.zone_id:
                if (name := data.get("name")) and (len(name) > 0):
                    self.name = name
                if (group_ids := data.get("groups")) and (len(group_ids) > 0):
                    self.group_ids = group_ids

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
