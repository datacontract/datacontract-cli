from os import getenv

from datacontract.storage import BaseDataContractStorage
from datacontract.storage.integrations import LocalDataContractStorage, GoogleCloudDataContractStorage


class DataContractStorageRegistry:
    """
    Registry for data contract storage classes.

    This class is responsible for returning the correct data contract storage class based on the storage type configuration.
    """

    _storage_classes = {"local": LocalDataContractStorage, "google_cloud": GoogleCloudDataContractStorage}

    @classmethod
    def get_storage(cls, storage_type: str = getenv("DATA_CONTRACT_STORAGE", "local")) -> BaseDataContractStorage:
        """
        Get the data contract storage class based on the storage type configuration.
        """
        if storage_type not in cls._storage_classes:
            raise ValueError(f"Storage type '{storage_type}' is not supported.")
        return cls._storage_classes[storage_type]
