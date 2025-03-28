import logging
from datetime import datetime, timezone
from enum import Enum
from typing import List
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
    id: str | None = None
    key: str | None = None
    category: str | None = None
    type: str
    name: str | None = None
    model: str | None = None
    field: str | None = None

    engine: str | None = None
    language: str | None = None
    implementation: str | None = None

    result: ResultEnum | None = None
    reason: str | None = None
    details: str | None = None
    diagnostics: dict | None = None


class Log(BaseModel):
    level: str
    message: str
    timestamp: datetime


class Run(BaseModel):
    runId: UUID
    dataContractId: str | None = None
    dataContractVersion: str | None = None
    dataProductId: str | None = None
    outputPortId: str | None = None
    server: str | None = None
    timestampStart: datetime | None
    timestampEnd: datetime | None
    result: ResultEnum = ResultEnum.unknown
    checks: List[Check] | None
    logs: List[Log] | None

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

    def pretty_logs(self) -> str:
        return "\n".join(f"[{log.timestamp.isoformat()}] {log.level}: {log.message}" for log in self.logs)

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
