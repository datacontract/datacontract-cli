from datacontract.config import Config
from datacontract.lint import files, s3, urls


def read_resource(location: str, config: Config | None = None) -> str:
    """
    Read a resource from a given location.

    Supported locations:
    - ``http://`` and ``https://`` URLs (API keys are supported)
    - ``s3://`` URLs
    - local file paths

    Args:
        location (str): The resource location.
        config: Optional credentials for authenticated URLs and ``s3://`` locations.

    Returns:
        str: The content of the resource.
    """
    if location.startswith("http://") or location.startswith("https://"):
        return urls.fetch_resource(location, config)
    elif location.startswith("s3://"):
        return s3.fetch_resource(location, config)
    else:
        return files.read_file(location)
