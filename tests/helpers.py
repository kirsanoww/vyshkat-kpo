from decimal import Decimal

from vyshkat.domain import ElectricScooter


def scooter(
    number: str = "S-1", *, score: int = 6, serviceable: bool = True, energy: str = "1.5"
) -> ElectricScooter:
    return ElectricScooter(
        name="Самокат",
        inventory_number=number,
        beginner_score=score,
        is_serviceable=serviceable,
        daily_energy_kwh=Decimal(energy),
    )
