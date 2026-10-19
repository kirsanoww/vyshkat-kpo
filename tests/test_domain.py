import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from tests.helpers import scooter
from vyshkat.domain import (
    Bicycle,
    ChargingStation,
    DockStation,
    ElectricBicycle,
    EnergyConsumer,
    Helmet,
    InventoryItem,
)


class DomainTests(unittest.TestCase):
    def test_all_assets_have_inventory_contract(self):
        assets = [
            scooter(),
            Bicycle(name="Велосипед", inventory_number="B", beginner_score=5, is_serviceable=True),
            Helmet(name="Шлем", inventory_number="H"),
            DockStation(name="Док", inventory_number="D"),
            ChargingStation(name="Зарядка", inventory_number="C", daily_energy_kwh=Decimal("2")),
        ]
        for asset in assets:
            with self.subTest(asset=type(asset).__name__):
                self.assertIsInstance(asset, InventoryItem)

    def test_only_powered_assets_have_energy_contract(self):
        self.assertIsInstance(scooter(), EnergyConsumer)
        self.assertIsInstance(
            ElectricBicycle(
                name="Электровелосипед",
                inventory_number="EB",
                beginner_score=6,
                is_serviceable=True,
                daily_energy_kwh=Decimal("1"),
            ),
            EnergyConsumer,
        )
        self.assertIsInstance(
            ChargingStation(name="Зарядка", inventory_number="C", daily_energy_kwh=Decimal("2")),
            EnergyConsumer,
        )
        self.assertNotIsInstance(Helmet(name="Шлем", inventory_number="H"), EnergyConsumer)
        self.assertNotIsInstance(
            Bicycle(name="Велосипед", inventory_number="B", beginner_score=5, is_serviceable=True),
            EnergyConsumer,
        )

    def test_blank_name_or_inventory_number_rejected(self):
        for field in ("name", "inventory_number"):
            for value in ("", "  ", None, 1):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    Helmet(**{"name": "Шлем", "inventory_number": "H", field: value})

    def test_surrounding_whitespace_is_removed(self):
        item = Helmet(name="  Шлем  ", inventory_number=" H-1 ")
        self.assertEqual((item.name, item.inventory_number), ("Шлем", "H-1"))

    def test_score_must_be_integer_between_one_and_ten(self):
        for score in (0, 11, -1, 5.5, True, "6", None):
            with self.subTest(score=score), self.assertRaises(ValueError):
                scooter(score=score)

    def test_score_bounds_are_valid(self):
        self.assertEqual(scooter(score=1).beginner_score, 1)
        self.assertEqual(scooter(score=10).beginner_score, 10)

    def test_serviceability_must_be_boolean(self):
        for value in (0, 1, "да", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scooter(serviceable=value)

    def test_invalid_energy_rejected_for_transport_and_items(self):
        for value in (Decimal("-1"), Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), 1.5):
            for model in (type(scooter()), ChargingStation):
                fields = {"name": "Объект", "inventory_number": "N", "daily_energy_kwh": value}
                if model is type(scooter()):
                    fields.update(beginner_score=6, is_serviceable=True)
                with self.subTest(model=model, energy=value), self.assertRaises(ValueError):
                    model(**fields)

    def test_zero_energy_is_valid(self):
        self.assertEqual(scooter(energy="0").daily_energy_kwh, Decimal("0"))

    def test_asset_fields_cannot_be_changed_after_admission(self):
        asset = scooter()
        for field, value in (("inventory_number", "S-2"), ("beginner_score", 0)):
            with self.subTest(field=field), self.assertRaises(FrozenInstanceError):
                setattr(asset, field, value)
