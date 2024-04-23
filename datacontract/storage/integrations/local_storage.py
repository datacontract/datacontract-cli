import os

from datacontract.storage import BaseDataContractStorage
from datacontract.model.exceptions import DataContractException


class LocalDataContractStorage(BaseDataContractStorage):
    """
    Local data contract storage.

    This class is responsible for saving, loading, deleting, and checking the existence of a data
    contract specification file.
    """

    def __init__(self, path: str = None, **kwargs):
        self.path = path
        self._abs_path = os.path.abspath(os.path.join(os.getcwd(), self.path)) if path else os.path.abspath(os.getcwd())
        if not os.path.exists(self.path) and self.path:
            os.makedirs(self.path)

    def get_file_path(self, file_name: str, sub_dir: str = None):
        """
        Get the file path.

        Args:
            file_name (str): The name of the file.
            sub_dir (str): The subdirectory to save the file in.

        Returns:
            str: The path to the file.
        """
        return os.path.join(self._abs_path, sub_dir, file_name) if sub_dir else os.path.join(self._abs_path, file_name)

    def save(self, data: str, file_name: str, sub_dir: str = None):
        """
        Save the data to the file. 'data' should be a YAML string. This method overwrites the file if it already exists.

        Args:
            file_name (str): The name of the file.
            data (str): The data to save.
            sub_dir (str): The subdirectory to save the file in.

        Returns:
            None
        """
        path = self.get_file_path(file_name, sub_dir)
        if sub_dir:
            os.makedirs(os.path.join(self._abs_path, sub_dir), exist_ok=True)
        with open(path, "w") as file:
            file.seek(0)
            file.write(data)

    def load(self, file_name: str, sub_dir: str = None) -> str:
        """
        Load the data from the file.

        Args:
            file_name (str): The name of the file.
            sub_dir (str): The subdirectory to save the file in.

        Returns:
            str: The data in the file.
        """
        path = self.get_file_path(file_name, sub_dir)
        if not self.exists(file_name, sub_dir):
            raise DataContractException(
                type="lint",
                name="Check that data contract YAML is valid",
                reason=f"The file '{file_name}' does not exist.",
            )
        with open(path) as f:
            return f.read()

    def delete(self, file_name: str, sub_dir: str = None):
        """
        Delete the file.

        Args:
            file_name (str): The name of the file.
            sub_dir (str): The subdirectory to save the file in.

        Returns:
            None
        """
        if not self.exists(file_name, sub_dir):
            return
        os.remove(self.get_file_path(file_name, sub_dir))

    def exists(self, file_name: str, sub_dir: str = None) -> bool:
        """
        Check if the file exists.

        Args:
            file_name (str): The name of the file.
            sub_dir (str): The subdirectory to save the file in.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        return os.path.exists(self.get_file_path(file_name, sub_dir))

    def get_file_uri(self, file_name: str, sub_dir: str = None):
        """
        Get the file path.
        """
        return self.get_file_path(file_name, sub_dir)
