"""Switch platform for Petkit Smart Devices integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pypetkitapi.command import FeederCommand, LBAction, LBCommand, LitterCommand
from pypetkitapi.const import (
    D3,
    D4H,
    D4S,
    D4SH,
    DEVICES_FEEDER,
    DEVICES_LITTER_BOX,
    T3,
    T4,
    T6,
)
from pypetkitapi.feeder_container import Feeder
from pypetkitapi.litter_container import Litter
from pypetkitapi.water_fountain_container import WaterFountain

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription

from .const import LOGGER
from .entity import PetKitDescSensorBase, PetkitEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PetkitDataUpdateCoordinator
    from .data import PetkitConfigEntry


@dataclass(frozen=True, kw_only=True)
class PetKitButtonDesc(PetKitDescSensorBase, ButtonEntityDescription):
    """A class that describes sensor entities."""

    action: Callable[PetkitConfigEntry]
    is_available: Callable[[Feeder | Litter | WaterFountain], bool] | None = None


BUTTON_MAPPING: dict[type[Feeder | Litter | WaterFountain], list[PetKitButtonDesc]] = {
    Feeder: [
        PetKitButtonDesc(
            key="Reset desiccant",
            translation_key="reset_desiccant",
            action=lambda api, device: api.send_api_request(
                device.id, FeederCommand.RESET_DESICCANT
            ),
            only_for_types=DEVICES_FEEDER,
        ),
        PetKitButtonDesc(
            key="Cancel manual feed",
            translation_key="cancel_manual_feed",
            action=lambda api, device: api.send_api_request(
                device.id, FeederCommand.CANCEL_MANUAL_FEED
            ),
            only_for_types=DEVICES_FEEDER,
        ),
        PetKitButtonDesc(
            key="Call pet",
            translation_key="call_pet",
            action=lambda api, device: api.send_api_request(
                device.id, FeederCommand.CALL_PET
            ),
            only_for_types=[D3],
        ),
        PetKitButtonDesc(
            key="Food replenished",
            translation_key="food_replenished",
            action=lambda api, device: api.send_api_request(
                device.id, FeederCommand.FOOD_REPLENISHED
            ),
            only_for_types=[D4S, D4H, D4SH],
        ),
    ],
    Litter: [
        PetKitButtonDesc(
            key="Scoop",
            translation_key="start_scoop",
            action=lambda api, device: api.send_api_request(
                device.id,
                LitterCommand.CONTROL_DEVICE,
                {LBAction.START: LBCommand.CLEANING},
            ),
            only_for_types=DEVICES_LITTER_BOX,
        ),
        PetKitButtonDesc(
            key="Maintenance mode",
            translation_key="start_maintenance",
            action=lambda api, device: api.send_api_request(
                device.id,
                LitterCommand.CONTROL_DEVICE,
                {LBAction.START: LBCommand.MAINTENANCE},
            ),
            only_for_types=[T4],
        ),
        PetKitButtonDesc(
            key="Exit maintenance mode",
            translation_key="exit_maintenance",
            action=lambda api, device: api.send_api_request(
                device.id,
                LitterCommand.CONTROL_DEVICE,
                {LBAction.END: LBCommand.MAINTENANCE},
            ),
            only_for_types=[T4],
        ),
        PetKitButtonDesc(
            key="Dump litter",
            translation_key="dump_litter",
            action=lambda api, device: api.send_api_request(
                device.id,
                LitterCommand.CONTROL_DEVICE,
                {LBAction.START: LBCommand.DUMPING},
            ),
            only_for_types=DEVICES_LITTER_BOX,
        ),
        PetKitButtonDesc(
            key="Pause",
            translation_key="action_pause",
            action=lambda api, device: api.send_api_request(
                device.id,
                LitterCommand.CONTROL_DEVICE,
                {
                    LBAction.STOP: api.petkit_entities[
                        device.id
                    ].state.work_state.work_mode
                },
            ),
            only_for_types=DEVICES_LITTER_BOX,
            is_available=lambda device: device.state.work_state is not None,
        ),
        PetKitButtonDesc(
            key="Continue",
            translation_key="action_continue",
            action=lambda api, device: api.send_api_request(
                device.id,
                LitterCommand.CONTROL_DEVICE,
                {
                    LBAction.CONTINUE: api.petkit_entities[
                        device.id
                    ].state.work_state.work_mode
                },
            ),
            only_for_types=DEVICES_LITTER_BOX,
            is_available=lambda device: device.state.work_state is not None,
        ),
        PetKitButtonDesc(
            key="Reset",
            translation_key="action_reset",
            action=lambda api, device: api.send_api_request(
                device.id,
                LitterCommand.CONTROL_DEVICE,
                {
                    LBAction.END: api.petkit_entities[
                        device.id
                    ].state.work_state.work_mode
                },
            ),
            only_for_types=DEVICES_LITTER_BOX,
            is_available=lambda device: device.state.work_state is not None,
        ),
        PetKitButtonDesc(
            key="Deodorize",
            translation_key="deodorize",
            action=lambda api, device: api.send_api_request(
                device.id,
                LitterCommand.CONTROL_DEVICE,
                {LBAction.START: LBCommand.ODOR_REMOVAL},
            ),
            only_for_types=[T4],
            value=lambda device: None if device.with_k3 == 0 else 1,
        ),
        PetKitButtonDesc(
            key="Reset odor eliminator",
            translation_key="reset_odor_eliminator",
            action=lambda api, device: api.send_api_request(
                device.id, LitterCommand.RESET_DEODORIZER
            ),
            only_for_types=[T3, T4, T6],
        ),
    ],
    WaterFountain: [
        # PetKitButtonDesc(
        #     key="Water filter reset",
        #     translation_key="water_filter_reset",
        #     action=lambda api, device: api.send_api_request(
        #         device.id, WaterFountainCommand.RESET_FILTER
        #     ),
        #     only_for_types=[D4S, D4H, D4SH]
        # ),
    ],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PetkitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary_sensors using config entry."""
    devices = entry.runtime_data.client.petkit_entities.values()
    entities = [
        PetkitButton(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
            device=device,
        )
        for device in devices
        for device_type, entity_descriptions in BUTTON_MAPPING.items()
        if isinstance(device, device_type)
        for entity_description in entity_descriptions
        if entity_description.is_supported(device)  # Check if the entity is supported
    ]
    async_add_entities(entities)


class PetkitButton(PetkitEntity, ButtonEntity):
    """Petkit Smart Devices Button class."""

    entity_description: PetKitButtonDesc

    def __init__(
        self,
        coordinator: PetkitDataUpdateCoordinator,
        entity_description: PetKitButtonDesc,
        device: Feeder | Litter | WaterFountain,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, device)
        self.coordinator = coordinator
        self.entity_description = entity_description
        self.device = device

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the binary_sensor."""
        return (
            f"{self.device.device_type}_{self.device.sn}_{self.entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Only make available if device is online."""
        device_data = self.coordinator.data.get(self.device.id)
        if self.entity_description.is_available:
            LOGGER.debug(
                "Button %s availability result is : %s",
                self.entity_description.key,
                self.entity_description.is_available(device_data),
            )
            return self.entity_description.is_available(device_data)
        return True

    async def async_press(self) -> None:
        """Handle the button press."""
        LOGGER.debug("Button pressed: %s", self.entity_description.key)
        await self.entity_description.action(
            self.coordinator.config_entry.runtime_data.client, self.device
        )
        await asyncio.sleep(1.5)
        await self.coordinator.async_request_refresh()
