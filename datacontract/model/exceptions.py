class DataContractException(Exception):
    """Exception raised for errors in the execution of a run.

    Attributes:
        type (str): The type of the error.
        name (str): The name associated with the error.
        model (str): The model involved in the error.
        reason (str): Explanation of the error.
        engine (str): The engine where the error occurred.
        original_exception (Exception, optional): Original exception that led to this error.
        message (str): General message for the error.
    """

    def __init__(
        self,
        type,
        name,
        reason,
        engine="datacontract",
        model=None,
        original_exception=None,
        result: str = "failed",
        message="Run operation failed",
    ):
        self.type = type
        self.name = name
        self.model = model
        self.reason = reason
        self.result = result
        self.engine = engine
        self.original_exception = original_exception
        self.message = message
        super().__init__(
            f"{self.message}: [{self.type}] {self.name} - {self.model} - {self.result} - {self.reason} - {self.engine}"
        )
