from abc import ABC, abstractmethod
from typing import List
from dataclasses import field, dataclass


@dataclass
class ImporterArgument:
    """
    Represents an argument for an importer.

    Attributes:
        name: The name of the argument.
        description: The description to pass to the user.
        required: Whether the argument is required.
    """

    name: str
    description: str = field(default="")
    required: bool = field(default=False)
    field_type: type = field(default=str)

    def convert(self, value):
        """
        Convert the value to the field type.
        """
        try:
            return self.field_type(value)
        except ValueError:
            raise ValueError(f"Could not convert {value} to '{self.field_type}'")


class BaseDataContractImporter(ABC):
    """
    Base class for importing data contracts from external sources.

    Attributes:
        _arguments: Contains the key-value pairs
    """

    _arguments: List[ImporterArgument]
    source: str

    def set_atributes(self, **kwargs):
        """
        Set the attributes of the class from arguments and kwargs.
        """
        for argument in self._arguments:
            if argument.required and argument.name not in kwargs:
                raise ValueError(f"Missing required argument '{argument.name}'")
            if argument.name in kwargs:
                setattr(self, argument.name, argument.convert(kwargs[argument.name]))

    @abstractmethod
    def import_from_source(self, **kwargs):
        """
        Import a data contract from an external source.

        :param kwargs: The key-value pairs of the source file.
        :return: The imported data contract.
        """
        pass

    def get_arguments(self):
        """
        Get the arguments for the importer.
        """
        return self._arguments
