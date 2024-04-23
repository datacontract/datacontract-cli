import os

from google.cloud.storage import Client

from datacontract.storage import BaseDataContractStorage
from datacontract.model.exceptions import DataContractException


class GoogleCloudDataContractStorage(BaseDataContractStorage):
    """
    Google Cloud Storage data contract storage.

    This class is responsible for saving, loading, deleting, and checking the existence of a data
    contract specification files in Google Cloud Storage.
    """

    def __init__(
        self, service_account_path: str = None, bucket_name: str = "datacontract", project_id: str = None, **kwargs
    ):
        """
        If service_account_path is None, the value of GOOGLE_APPLICATION_CREDENTIALS environment variable is used.
        If project_id is None, the value from the service account file is used.
        """
        if service_account_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path

        if not service_account_path and "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            raise DataContractException(
                type="storage",
                name="Google Cloud Storage",
                reason="Service account path is not provided.",
            )
        self._gs_client = Client(project=project_id) if project_id else Client()
        self._bucket = self._gs_client.bucket(bucket_name)
        if not self._bucket.exists():
            raise DataContractException(
                type="storage",
                name="Google Cloud Storage",
                reason=f"The bucket '{bucket_name}' does not exist.",
            )

    @staticmethod
    def join_path(*args):
        """
        Join the path components.
        """
        elements = []
        for arg in args:
            if arg:
                elements.extend(arg.split("/"))
        return "/".join(elements)

    def get_file_path(self, file_name: str, sub_dir: str = None) -> str:
        """
        Get the file path.

        Args:
            file_name (str): The name of the file.
            sub_dir (str): The subdirectory to save the file in.

        Returns:
            str: The path to the file.
        """
        return self.join_path(sub_dir, file_name)

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
        blob = self._bucket.blob(self.get_file_path(file_name, sub_dir))
        blob.upload_from_string(data)

    def load(self, file_name: str, sub_dir: str = None) -> str:
        """
        Load the data from the file.

        Args:
            file_name (str): The name of the file.
            sub_dir (str): The subdirectory to save the file in.

        Returns:
            str: The data in the file.
        """
        if not self.exists(file_name, sub_dir):
            raise DataContractException(
                type="storage",
                name="Google Cloud Storage",
                reason=f"The file '{file_name}' does not exist.",
            )
        blob = self._bucket.blob(self.get_file_path(file_name, sub_dir))
        return blob.download_as_string().decode("utf-8")

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
        blob = self._bucket.blob(self.get_file_path(file_name, sub_dir))
        blob.delete()

    def exists(self, file_name: str, sub_dir: str = None) -> bool:
        """
        Check if the file exists.

        Args:
            file_name (str): The name of the file.
            sub_dir (str): The subdirectory to save the file in.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        blob = self._bucket.blob(self.get_file_path(file_name, sub_dir))
        return blob.exists()

    def get_file_uri(self, file_name: str, sub_dir: str = None):
        """
        Get the file uri. Example: gs://datacontract/file_name.yaml
        """
        return f"gs://{self._bucket.name}/{self.get_file_path(file_name, sub_dir)}"
