from dataclasses import dataclass
from datetime import datetime, timedelta

from src.exceptions import LicenseValidationError

@dataclass(frozen=True)
class LicenseClockState:
    version: int
    machine_id: str
    last_run_utc: datetime

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "LicenseClockState":
        expected_fields = {"version", "machine_id", "last_run_utc"}
        if not isinstance(data, dict) or set(data) != expected_fields:
            raise LicenseValidationError("Invalid license clock state format.")

        if (
            type(data["version"]) is not int or
            not isinstance(data["machine_id"], str) or 
            not isinstance(data["last_run_utc"], str)
        ):
            raise LicenseValidationError("Invalid license clock state format.")
        
        try:
            last_run_utc = datetime.fromisoformat(data["last_run_utc"])
        except ValueError as error:
            raise LicenseValidationError("Invalid license clock state format.") from error

        if last_run_utc.tzinfo is None or last_run_utc.utcoffset() != timedelta(0):
            raise LicenseValidationError("Invalid license clock state format.")
        
        return cls(data["version"], data["machine_id"], last_run_utc)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "machine_id": self.machine_id,
            "last_run_utc": self.last_run_utc.isoformat(timespec="seconds")
        }