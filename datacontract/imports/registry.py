from typing import List
import importlib
import pkgutil
import inspect

from datacontract.imports import BaseDataContractImporter
import datacontract.imports.integrations as integrations


class DataContractsImporterRegistry:
    """
    Registry class to store references to all the data contracts importers available.
    """

    _importers = {}

    def __init__(self):
        # Import all the importers from the integrations package.
        # This is done dynamically enabling the addition of new importers without changing the registry.
        for module_info in pkgutil.iter_modules(integrations.__path__):
            module_name = f"{integrations.__name__}.{module_info.name}"
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseDataContractImporter) and name != "BaseDataContractImporter":
                    self._importers[obj.source] = obj

    def has_importer(self, name) -> bool:
        """
        Check if the importer exists in the registry.

        :param name: The name of the importer.
        :return: Whether the importer exists.
        """
        return name in self._importers

    def get_importer(self, name) -> BaseDataContractImporter:
        """
        Get an importer from the registry.

        :param name: The name of the importer.
        :return: The importer.
        """
        return self._importers[name]()

    def list_importers(self) -> List[str]:
        """
        List all the importers in the registry.
        """
        return list(self._importers.keys())
