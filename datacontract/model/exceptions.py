from datacontract.model.run import ResultEnum


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
        result: ResultEnum = ResultEnum.failed,
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


class DataContractValidationErrors(DataContractException):
    def __init__(self, errors: list[DataContractException]):
        self.errors = errors
        first_error = errors[0]
        super().__init__(
            type=first_error.type,
            name=first_error.name,
            reason=first_error.reason,
            engine=first_error.engine,
            model=first_error.model,
            original_exception=first_error.original_exception,
            result=first_error.result,
            message="Run operation failed with multiple validation errors",
        )
