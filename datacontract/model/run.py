import logging
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel


class ResultEnum(str, Enum):
    passed = "passed"
    warning = "warning"
    failed = "failed"
    error = "error"
    info = "info"
    unknown = "unknown"


class Check(BaseModel):
    type: str
    name: Optional[str]
    result: ResultEnum
    engine: str
    reason: Optional[str] = None
    model: Optional[str] = None
    field: Optional[str] = None
    details: Optional[str] = None
    diagnostics: Optional[dict] = None


class Log(BaseModel):
    level: str
    message: str
    timestamp: datetime


class Run(BaseModel):
    runId: UUID
    dataContractId: Optional[str] = None
    dataContractVersion: Optional[str] = None
    dataProductId: Optional[str] = None
    outputPortId: Optional[str] = None
    server: Optional[str] = None
    timestampStart: datetime
    timestampEnd: datetime
    result: ResultEnum = ResultEnum.unknown
    checks: List[Check]
    logs: List[Log]

    def has_passed(self):
        self.calculate_result()
        return self.result == ResultEnum.passed

    def finish(self):
        self.timestampEnd = datetime.now(timezone.utc)
        self.calculate_result()

    def calculate_result(self):
        if any(check.result == ResultEnum.error for check in self.checks):
            self.result = ResultEnum.error
        elif any(check.result == ResultEnum.failed for check in self.checks):
            self.result = ResultEnum.failed
        elif any(check.result == ResultEnum.warning for check in self.checks):
            self.result = ResultEnum.warning
        elif any(check.result == ResultEnum.passed for check in self.checks):
            self.result = ResultEnum.passed
        else:
            self.result = ResultEnum.unknown

    def log_info(self, message: str):
        logging.info(message)
        self.logs.append(Log(level="INFO", message=message, timestamp=datetime.now(timezone.utc)))

    def log_warn(self, message: str):
        logging.warning(message)
        self.logs.append(Log(level="WARN", message=message, timestamp=datetime.now(timezone.utc)))

    def log_error(self, message: str):
        logging.error(message)
        self.logs.append(Log(level="ERROR", message=message, timestamp=datetime.now(timezone.utc)))

    def pretty(self):
        return self.model_dump_json(indent=2)

    @staticmethod
    def create_run():
        """
        Factory method to create a new Run instance.

        :return: An instance of Run.
        """
        run_id = uuid4()
        now = datetime.now(timezone.utc)
        return Run(
            runId=run_id,
            timestampStart=now,
            timestampEnd=now,
            checks=[],
            logs=[],
        )
