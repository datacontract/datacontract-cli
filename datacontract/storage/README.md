## Data Contract CLI Storage

This is a set of tools to manage the storage of data contracts.

### Registry

The registry is a simple key-value store that maps a storage type name to a class object.
The registry is used to return an object based on key words of the storage type used. Currently, only the following types are supported:

- Local
- Google Cloud Storage

#### Benefits of using the registry

- The registry allows for easy extension of storage types.
- The registry allows for easy retrieval of storage types based on key words.

#### How to registry a new storage type

To register a new storage type, you need to create a new class that inherits from the `BaseDataContractStorage` 
class and implement the abstract methods. Then, you need to add the new class to the atrribute `storage_registry`
in the class `DataContractStorageRegistry`.

Ex.:
  
  ```python
  class DataContractStorageRegistry:
    """
    Registry for data contract storage classes.

    This class is responsible for returning the correct data contract storage class based on the storage type configuration.
    """

    _storage_classes = {
      "local": LocalDataContractStorage, 
      "google_cloud": GoogleCloudDataContractStorage,
      "new_storage_type": NewStorageTypeDataContractStorage
    }
    ...
  ```

### BaseDataContractStorage

The `BaseDataContractStorage` class is an abstract class that defines the methods that a storage class should implement. The methods are:

- `save`: Saves a file to the storage.
- `load`: Downloads a file from the storage.
- `delete`: Deletes a file from the storage.
- `exists`: Checks if a file exists in the storage.
- `get_file_uri`: Returns the URI of a file in the storage.

### Future Work

- Add more storage types.
- Enables the user to register a new custom storage type (lazy import?).