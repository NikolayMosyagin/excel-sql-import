from dataclasses import dataclass

from src.exceptions import LicenseValidationError


@dataclass(frozen=True)
class LicensePayload:
    version: int
    license_id: str
    machine_id: str
    issued_at: str
    expires_at: str

    @classmethod
    def from_json(cls, data: dict[str, object]) -> "LicensePayload":
        expected_fields = {"version", "license_id", "machine_id", "issued_at", "expires_at"}
        if not isinstance(data, dict) or expected_fields != set(data):
            raise LicenseValidationError("Invalid license format.")
        
        if (
            type(data["version"]) is not int or
            not isinstance(data["license_id"], str) or
            not isinstance(data["machine_id"], str) or
            not isinstance(data["issued_at"], str) or
            not isinstance(data["expires_at"], str)
        ):
            raise LicenseValidationError("Invalid license format.")
        
        return cls(**data)


@dataclass(frozen=True)
class License:
    payload: LicensePayload
    signature: str

    @classmethod
    def from_json(cls, data: dict[str, object]) -> "License":
        if not isinstance(data, dict) or set(data) != {"payload", "signature"}:
            raise LicenseValidationError("Invalid license format.")
        
        if not isinstance(data["signature"], str):
            raise LicenseValidationError("Invalid license format.")
        
        return cls(LicensePayload.from_json(data["payload"]), data["signature"])