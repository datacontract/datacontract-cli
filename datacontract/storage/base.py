from abc import ABCMeta, abstractmethod


class BaseDataContractStorage(metaclass=ABCMeta):
    """
    Base class for data contract storage.

    Definition: A data contract storage is a class that is responsible
    for saving, loading, deleting, and checking the existence of a data contract specification file.
    """

    @abstractmethod
    def save(self, data: str, file_name: str, sub_dir: str = None):
        """
        Save the data to the file. 'data' should be a YAML string.
        """
        pass

    @abstractmethod
    def load(self, file_name: str, sub_dir: str = None):
        """
        Load the data from the file.
        """
        pass

    @abstractmethod
    def delete(self, file_name: str, sub_dir: str = None):
        """
        Delete the file.
        """
        pass

    @abstractmethod
    def exists(self, file_name: str, sub_dir: str = None):
        """
        Check if the file exists.
        """
        pass

    @abstractmethod
    def get_file_uri(self, file_name: str, sub_dir: str = None):
        """
        Get the file URI.
        """
        pass
