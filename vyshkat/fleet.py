"""Приёмка, баланс и отчёты. Ввод и печать остаются за пределами сервиса."""

from dataclasses import dataclass
from decimal import Decimal

from vyshkat.domain import EnergyConsumer, InventoryItem, Item, Vehicle
from vyshkat.inspection import InspectionResult, ServiceCenter


@dataclass(frozen=True)
class FleetReport:
    vehicle_count: int
    item_count: int
    vehicle_energy_kwh: Decimal
    total_energy_kwh: Decimal

    @property
    def total_count(self) -> int:
        return self.vehicle_count + self.item_count


class FleetService:
    def __init__(self, service_center: ServiceCenter) -> None:
        self._service_center = service_center
        self._assets: dict[str, InventoryItem] = {}

    def _check_number(self, asset: InventoryItem) -> None:
        if asset.inventory_number in self._assets:
            raise ValueError(f"Инвентарный номер {asset.inventory_number!r} уже занят.")

    def add_vehicle(self, vehicle: Vehicle) -> InspectionResult:
        if not isinstance(vehicle, Vehicle):
            raise ValueError("В парк можно принять только транспортное средство.")
        self._check_number(vehicle)
        result = self._service_center.inspect(vehicle)
        if result.accepted:
            self._assets[vehicle.inventory_number] = vehicle
        return result

    def add_item(self, item: Item) -> None:
        if not isinstance(item, Item):
            raise ValueError("На баланс вещей можно поставить только инвентарь.")
        self._check_number(item)
        self._assets[item.inventory_number] = item

    def inventory(self) -> tuple[InventoryItem, ...]:
        return tuple(self._assets.values())

    def beginner_vehicles(self) -> tuple[Vehicle, ...]:
        return tuple(
            asset
            for asset in self._assets.values()
            if isinstance(asset, Vehicle) and asset.beginner_score >= 6
        )

    @staticmethod
    def _energy(assets: tuple[InventoryItem, ...]) -> Decimal:
        return sum(
            (asset.daily_energy_kwh for asset in assets if isinstance(asset, EnergyConsumer)),
            start=Decimal("0"),
        )

    def report(self) -> FleetReport:
        assets = self.inventory()
        vehicles = tuple(asset for asset in assets if isinstance(asset, Vehicle))
        return FleetReport(
            vehicle_count=len(vehicles),
            item_count=len(assets) - len(vehicles),
            vehicle_energy_kwh=self._energy(vehicles),
            total_energy_kwh=self._energy(assets),
        )
