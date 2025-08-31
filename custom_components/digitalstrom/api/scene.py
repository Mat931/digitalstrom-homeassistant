from .apartment import DigitalstromApartment
from .exceptions import ServerError
from .zone import DigitalstromZone


class DigitalstromScene:
    def __init__(self):
        pass

    async def call(self) -> None:
        pass

    async def undo(self) -> None:
        pass


class DigitalstromApartmentScene(DigitalstromScene):
    def __init__(
        self,
        apartment: DigitalstromApartment,
        name: str,
        call_number: int,
        undo_number: int = None,
        state_name: str = None,
        on_state: str = None,
    ):
        self.apartment = apartment
        self.name = name
        self.call_number = call_number
        self.undo_number = undo_number
        self.state_name = state_name
        self.on_state = on_state
        self.last_value = None

    async def call(self, force: bool = False) -> None:
        await self.apartment.call_scene(self.call_number, force)

    async def undo(self, force: bool = False) -> None:
        if self.undo_number is None:
            await self.apartment.undo_scene(self.call_number)
        else:
            await self.apartment.call_scene(self.undo_number, force)

    async def get_value(self) -> bool:
        if self.state_name is None or self.on_state is None:
            return None
        try:
            result = await self.apartment.client.request(
                f"property/getString?path=/usr/states/{self.state_name}/state"
            )
            self.last_value = result.get("value", None)
            if self.last_value is not None:
                self.last_value = self.last_value == self.on_state
        except ServerError:
            self.last_value = None
        return self.last_value


class DigitalstromZoneScene(DigitalstromScene):
    def __init__(
        self,
        zone: DigitalstromZone,
        number: int,
        group: int,
        name: str = None,
    ):
        self.zone = zone
        self.name = name
        self.number = number
        self.group = group

    async def call(self, force: bool = False) -> None:
        await self.zone.call_scene(self.number, self.group, force)

    async def undo(self) -> None:
        await self.zone.undo_scene(self.number, self.group)
