"""Единственное место сборки зависимостей приложения."""

from dependency_injector import containers, providers

from vyshkat.cli import ConsoleApp
from vyshkat.fleet import FleetService
from vyshkat.inspection import BasicServiceCenter


class Container(containers.DeclarativeContainer):
    service_center = providers.Factory(BasicServiceCenter)
    fleet = providers.Singleton(FleetService, service_center=service_center)
    console = providers.Factory(ConsoleApp, fleet=fleet)
