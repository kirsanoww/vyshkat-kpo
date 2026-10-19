"""Контракт техосмотра и простая реализация правил приёмки."""

from dataclasses import dataclass
from typing import Protocol

from vyshkat.domain import Vehicle


@dataclass(frozen=True)
class InspectionResult:
    accepted: bool
    reason: str


class ServiceCenter(Protocol):
    def inspect(self, vehicle: Vehicle) -> InspectionResult: ...


class BasicServiceCenter:
    """В учебной модели оператор передаёт результат проверки исправности."""

    def inspect(self, vehicle: Vehicle) -> InspectionResult:
        if vehicle.is_serviceable:
            return InspectionResult(True, "Техника исправна, техосмотр пройден.")
        return InspectionResult(False, "Обнаружена неисправность: требуется ремонт.")
