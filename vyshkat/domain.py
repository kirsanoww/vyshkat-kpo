"""Объекты предметной области и их инварианты. Не зависят от интерфейса и DI."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@runtime_checkable
class InventoryItem(Protocol):
    """Минимальный контракт объекта, стоящего на балансе."""

    @property
    def name(self) -> str: ...

    @property
    def inventory_number(self) -> str: ...


@runtime_checkable
class EnergyConsumer(Protocol):
    """Контракт потребителя электроэнергии, независимо от вида объекта."""

    @property
    def daily_energy_kwh(self) -> Decimal: ...


def validate_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Текстовое поле не может быть пустым.")
    return value.strip()


def validate_score(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 10:
        raise ValueError("Простота для новичка должна быть целым числом от 1 до 10.")
    return value


def validate_energy(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError("Расход энергии должен быть конечным неотрицательным числом.")
    return value


@dataclass(frozen=True, kw_only=True)
class Asset:
    name: str
    inventory_number: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", validate_text(self.name))
        object.__setattr__(self, "inventory_number", validate_text(self.inventory_number))


@dataclass(frozen=True, kw_only=True)
class Vehicle(Asset):
    beginner_score: int
    is_serviceable: bool

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_score(self.beginner_score)
        if type(self.is_serviceable) is not bool:
            raise ValueError("Исправность должна быть логическим значением.")


@dataclass(frozen=True, kw_only=True)
class ElectricVehicle(Vehicle):
    daily_energy_kwh: Decimal

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_energy(self.daily_energy_kwh)


class ElectricScooter(ElectricVehicle):
    """Электросамокат."""


class Bicycle(Vehicle):
    """Обычный велосипед: не является потребителем электроэнергии."""


class ElectricBicycle(ElectricVehicle):
    """Электровелосипед."""


class Item(Asset):
    """Инвентарь, не являющийся прокатным транспортом."""


class Helmet(Item):
    """Защитный шлем."""


class DockStation(Item):
    """Механическая док-станция без зарядки."""


@dataclass(frozen=True, kw_only=True)
class ChargingStation(Item):
    daily_energy_kwh: Decimal

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_energy(self.daily_energy_kwh)
