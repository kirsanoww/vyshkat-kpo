"""Консольный интерфейс; тот же диалог можно читать из текстового файла."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TextIO, TypeVar

from vyshkat.domain import (
    Asset,
    Bicycle,
    ChargingStation,
    DockStation,
    ElectricBicycle,
    ElectricScooter,
    Helmet,
    Item,
    Vehicle,
    validate_energy,
    validate_score,
    validate_text,
)
from vyshkat.fleet import FleetService

T = TypeVar("T")


@dataclass(frozen=True)
class AssetType:
    label: str
    model: type[Asset]
    consumes_energy: bool = False


VEHICLE_TYPES = {
    "1": AssetType("Электросамокат", ElectricScooter, True),
    "2": AssetType("Велосипед", Bicycle),
    "3": AssetType("Электровелосипед", ElectricBicycle, True),
}
ITEM_TYPES = {
    "1": AssetType("Шлем", Helmet),
    "2": AssetType("Док-станция без зарядки", DockStation),
    "3": AssetType("Зарядная станция", ChargingStation, True),
}


def parse_score(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ValueError("Введите целое число от 1 до 10.") from None
    return validate_score(value)


def parse_energy(raw: str) -> Decimal:
    try:
        value = Decimal(raw.replace(",", "."))
    except InvalidOperation:
        raise ValueError("Введите расход числом, например 1.5.") from None
    return validate_energy(value)


def parse_bool(raw: str) -> bool:
    value = raw.casefold()
    if value in {"да", "д", "yes", "y", "1"}:
        return True
    if value in {"нет", "н", "no", "n", "0"}:
        return False
    raise ValueError("Введите «да» или «нет».")


class ConsoleApp:
    def __init__(self, fleet: FleetService) -> None:
        self._fleet = fleet

    def _print(self, text: str) -> None:
        print(text, file=self._output)

    def _read(self, prompt: str) -> str:
        print(prompt, end="", file=self._output, flush=True)
        while True:
            line = self._input.readline()
            if not line:
                raise EOFError
            if line.lstrip().startswith("#"):
                continue
            if self._echo:
                self._print(line.rstrip("\r\n"))
            return line.strip()

    def _ask(self, prompt: str, parse: Callable[[str], T]) -> T:
        while True:
            try:
                return parse(self._read(prompt))
            except ValueError as error:
                self._print(f"Ошибка: {error}")

    def _select_type(self, options: dict[str, AssetType]) -> AssetType:
        for key, option in options.items():
            self._print(f"{key}. {option.label}")

        def parse(raw: str) -> AssetType:
            if raw not in options:
                raise ValueError("Выберите один из перечисленных типов.")
            return options[raw]

        return self._ask("Тип: ", parse)

    def _add_asset(self, options: dict[str, AssetType]) -> None:
        option = self._select_type(options)
        fields = {
            "name": self._ask("Наименование: ", validate_text),
            "inventory_number": self._ask("Инвентарный номер: ", validate_text),
        }
        if issubclass(option.model, Vehicle):
            fields["beginner_score"] = self._ask("Простота для новичка (1–10): ", parse_score)
            fields["is_serviceable"] = self._ask("Техника исправна (да/нет): ", parse_bool)
        if option.consumes_energy:
            fields["daily_energy_kwh"] = self._ask("Энергия за сутки (кВт·ч): ", parse_energy)

        asset = option.model(**fields)
        if isinstance(asset, Vehicle):
            result = self._fleet.add_vehicle(asset)
            status = "Принято в парк" if result.accepted else "Отклонено"
            self._print(f"{status}: {asset.name}. {result.reason}")
        elif isinstance(asset, Item):
            self._fleet.add_item(asset)
            self._print(f"Добавлено на баланс: {asset.name}.")

    def _report(self) -> None:
        report = self._fleet.report()
        self._print(f"Транспорт: {report.vehicle_count}")
        self._print(f"Вещи: {report.item_count}")
        self._print(f"Всего на балансе: {report.total_count}")
        self._print(f"Энергия транспорта за сутки: {report.vehicle_energy_kwh} кВт·ч")
        self._print(f"Энергия всего баланса за сутки: {report.total_energy_kwh} кВт·ч")

    def _beginners(self) -> None:
        vehicles = self._fleet.beginner_vehicles()
        if not vehicles:
            self._print("Нет транспорта для новичков.")
        for vehicle in vehicles:
            self._print(
                f"{vehicle.inventory_number} | {vehicle.name} | простота {vehicle.beginner_score}"
            )

    def _inventory(self) -> None:
        assets = self._fleet.inventory()
        if not assets:
            self._print("Баланс пуст.")
        for asset in assets:
            self._print(f"{asset.inventory_number} | {asset.name}")

    def run(self, input_stream: TextIO, output_stream: TextIO, *, echo: bool = False) -> int:
        self._input, self._output, self._echo = input_stream, output_stream, echo
        actions = {
            "1": lambda: self._add_asset(VEHICLE_TYPES),
            "2": lambda: self._add_asset(ITEM_TYPES),
            "3": self._report,
            "4": self._beginners,
            "5": self._inventory,
        }
        self._print("ВышКат — учёт парка. Данные хранятся до выхода из приложения.")
        while True:
            self._print(
                "\n1. Принять транспорт\n2. Добавить вещь\n3. Отчёт"
                "\n4. Транспорт для новичков\n5. Инвентаризация\n0. Выход"
            )
            try:
                command = self._read("Команда: ")
            except (EOFError, KeyboardInterrupt):
                self._print("\nВвод завершён.")
                return 0
            if command == "0":
                self._print("Работа завершена.")
                return 0
            action = actions.get(command)
            if action is None:
                self._print("Неизвестная команда. Выберите пункт меню.")
                continue
            try:
                action()
            except ValueError as error:
                self._print(f"Ошибка: {error}")
            except (EOFError, KeyboardInterrupt):
                self._print("\nВвод прерван: незавершённый объект не добавлен.")
                return 1
