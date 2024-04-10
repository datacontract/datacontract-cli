import os


def read_file(file: str) -> str:
    """
    Read the content of a file
    @param file: file path
    @return: the file content as a string
    """
    if not os.path.exists(file):
        raise f"The file '{file}' does not exist."
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
