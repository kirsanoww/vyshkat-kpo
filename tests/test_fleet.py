import unittest
from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import Mock

from tests.helpers import scooter
from vyshkat.domain import Bicycle, ChargingStation, ElectricVehicle, Helmet, Item
from vyshkat.fleet import FleetService
from vyshkat.inspection import BasicServiceCenter, InspectionResult, ServiceCenter


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.fleet = FleetService(BasicServiceCenter())

    def test_empty_fleet_reports_zero(self):
        report = self.fleet.report()
        self.assertEqual((report.vehicle_count, report.item_count, report.total_count), (0, 0, 0))
        self.assertEqual(report.total_energy_kwh, Decimal("0"))
        self.assertEqual(report.vehicle_energy_kwh, Decimal("0"))
        self.assertEqual(self.fleet.inventory(), ())
        self.assertEqual(self.fleet.beginner_vehicles(), ())

    def test_serviceable_vehicle_is_accepted(self):
        vehicle = scooter()
        result = self.fleet.add_vehicle(vehicle)
        self.assertTrue(result.accepted)
        self.assertTrue(result.reason)
        self.assertEqual(self.fleet.inventory(), (vehicle,))

    def test_rejected_vehicle_does_not_affect_any_report(self):
        result = self.fleet.add_vehicle(scooter(serviceable=False))
        self.assertFalse(result.accepted)
        self.assertIn("ремонт", result.reason)
        self.assertEqual(self.fleet.inventory(), ())
        self.assertEqual(self.fleet.beginner_vehicles(), ())
        self.assertEqual(self.fleet.report().total_count, 0)
        self.assertEqual(self.fleet.report().total_energy_kwh, Decimal("0"))

    def test_rejection_does_not_reserve_inventory_number(self):
        self.fleet.add_vehicle(scooter(serviceable=False))
        self.assertTrue(self.fleet.add_vehicle(scooter()).accepted)
        self.assertEqual(self.fleet.report().vehicle_count, 1)

    def test_inspection_happens_before_vehicle_is_added(self):
        center = Mock(spec=ServiceCenter)
        fleet = FleetService(center)

        def inspect(vehicle):
            self.assertEqual(fleet.inventory(), ())
            return InspectionResult(True, "Проверено")

        center.inspect.side_effect = inspect
        vehicle = scooter()
        fleet.add_vehicle(vehicle)
        center.inspect.assert_called_once_with(vehicle)

    def test_inspection_error_does_not_add_vehicle(self):
        center = Mock(spec=ServiceCenter)
        center.inspect.side_effect = RuntimeError("Сервис недоступен")
        fleet = FleetService(center)
        with self.assertRaises(RuntimeError):
            fleet.add_vehicle(scooter())
        self.assertEqual(fleet.inventory(), ())

    def test_beginner_threshold_is_six(self):
        for score in (1, 5, 6, 10):
            self.fleet.add_vehicle(scooter(f"S-{score}", score=score))
        self.fleet.add_item(Helmet(name="Шлем", inventory_number="H"))
        self.assertEqual(
            [vehicle.beginner_score for vehicle in self.fleet.beginner_vehicles()], [6, 10]
        )

    def test_bicycle_can_be_suitable_for_beginners_without_using_energy(self):
        bike = Bicycle(
            name="Велосипед", inventory_number="B", beginner_score=8, is_serviceable=True
        )
        self.fleet.add_vehicle(bike)
        self.assertEqual(self.fleet.beginner_vehicles(), (bike,))
        self.assertEqual(self.fleet.report().total_energy_kwh, Decimal("0"))

    def test_report_includes_energy_of_items_and_separates_transport(self):
        self.fleet.add_vehicle(scooter(energy="0.1"))
        self.fleet.add_vehicle(scooter("S-2", energy="0.2"))
        self.fleet.add_item(Helmet(name="Шлем", inventory_number="H"))
        self.fleet.add_item(
            ChargingStation(name="Зарядка", inventory_number="C", daily_energy_kwh=Decimal("0.4"))
        )
        report = self.fleet.report()
        self.assertEqual((report.vehicle_count, report.item_count, report.total_count), (2, 2, 4))
        self.assertEqual(report.vehicle_energy_kwh, Decimal("0.3"))
        self.assertEqual(report.total_energy_kwh, Decimal("0.7"))

    def test_duplicate_vehicle_is_rejected_before_inspection(self):
        center = Mock(spec=ServiceCenter)
        center.inspect.return_value = InspectionResult(True, "ОК")
        fleet = FleetService(center)
        fleet.add_vehicle(scooter())
        with self.assertRaisesRegex(ValueError, "уже занят"):
            fleet.add_vehicle(scooter(energy="7"))
        self.assertEqual(center.inspect.call_count, 1)
        self.assertEqual(fleet.report().total_energy_kwh, Decimal("1.5"))

    def test_inventory_numbers_are_unique_across_transport_and_items(self):
        self.fleet.add_vehicle(scooter("N"))
        with self.assertRaises(ValueError):
            self.fleet.add_item(Helmet(name="Шлем", inventory_number=" N "))
        self.fleet.add_item(Helmet(name="Шлем", inventory_number="H"))
        with self.assertRaises(ValueError):
            self.fleet.add_vehicle(scooter("H"))
        with self.assertRaises(ValueError):
            self.fleet.add_item(Helmet(name="Другой шлем", inventory_number="H"))
        self.assertEqual(self.fleet.report().total_count, 2)

    def test_vehicle_cannot_bypass_inspection_as_item(self):
        with self.assertRaises(ValueError):
            self.fleet.add_item(scooter(serviceable=False))
        with self.assertRaises(ValueError):
            self.fleet.add_vehicle(Helmet(name="Шлем", inventory_number="H"))
        self.assertEqual(self.fleet.inventory(), ())

    def test_employee_cannot_be_put_on_balance(self):
        @dataclass
        class Employee:
            name: str

        for add in (self.fleet.add_item, self.fleet.add_vehicle):
            with self.subTest(method=add.__name__), self.assertRaises(ValueError):
                add(Employee("Иван"))
        self.assertEqual(self.fleet.inventory(), ())

    def test_inventory_is_a_snapshot_not_a_mutable_storage(self):
        first = scooter()
        self.fleet.add_vehicle(first)
        snapshot = self.fleet.inventory()
        second = Helmet(name="Шлем", inventory_number="H")
        self.fleet.add_item(second)
        self.assertEqual(snapshot, (first,))
        self.assertEqual(self.fleet.inventory(), (first, second))

    def test_new_transport_type_works_without_changing_fleet_service(self):
        class ElectricTricycle(ElectricVehicle):
            pass

        vehicle = ElectricTricycle(
            name="Электротрицикл",
            inventory_number="T",
            beginner_score=7,
            is_serviceable=True,
            daily_energy_kwh=Decimal("2.5"),
        )
        self.assertTrue(self.fleet.add_vehicle(vehicle).accepted)
        self.assertEqual(self.fleet.beginner_vehicles(), (vehicle,))
        self.assertEqual(self.fleet.report().vehicle_energy_kwh, Decimal("2.5"))

    def test_new_powered_item_is_counted_by_protocol(self):
        @dataclass(frozen=True, kw_only=True)
        class ChargingCabinet(Item):
            daily_energy_kwh: Decimal

        self.fleet.add_item(
            ChargingCabinet(name="Шкаф", inventory_number="C", daily_energy_kwh=Decimal("3"))
        )
        self.assertEqual(self.fleet.report().total_energy_kwh, Decimal("3"))
        self.assertEqual(self.fleet.report().vehicle_energy_kwh, Decimal("0"))
        self.assertEqual(self.fleet.beginner_vehicles(), ())
