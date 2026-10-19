import unittest
from unittest.mock import Mock

from dependency_injector import providers

from tests.helpers import scooter
from vyshkat.container import Container
from vyshkat.inspection import InspectionResult, ServiceCenter


class ContainerTests(unittest.TestCase):
    def test_inspection_rejection_can_be_injected_through_container(self):
        center = Mock(spec=ServiceCenter)
        center.inspect.return_value = InspectionResult(False, "Запрет тестового сервиса")
        container = Container()
        with container.service_center.override(providers.Object(center)):
            fleet = container.fleet()
            vehicle = scooter(serviceable=True)
            result = fleet.add_vehicle(vehicle)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "Запрет тестового сервиса")
        self.assertEqual(fleet.inventory(), ())
        center.inspect.assert_called_once_with(vehicle)

    def test_fleet_uses_injected_decision_without_repeating_inspection(self):
        center = Mock(spec=ServiceCenter)
        center.inspect.return_value = InspectionResult(True, "Разрешение тестового сервиса")
        container = Container()
        with container.service_center.override(providers.Object(center)):
            fleet = container.fleet()
            vehicle = scooter(serviceable=False)
            self.assertTrue(fleet.add_vehicle(vehicle).accepted)
        self.assertEqual(fleet.inventory(), (vehicle,))
        center.inspect.assert_called_once_with(vehicle)

    def test_one_container_reuses_fleet_instance(self):
        container = Container()
        self.assertIs(container.fleet(), container.fleet())

    def test_different_containers_have_independent_state(self):
        first, second = Container(), Container()
        first.fleet().add_vehicle(scooter())
        self.assertEqual(second.fleet().inventory(), ())
