import base64
import binascii
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from src.license_model import License, LicensePayload
from src.license_clock import check_license_clock
from src.exceptions import LicenseValidationError


SUPPORTED_LICENSE_VERSION = 1


def load_license(license_path: Path) -> License:

    try:
        with open(license_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as error:
        raise LicenseValidationError(f"License file {license_path} not found.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise LicenseValidationError("Invalid license JSON format.") from error
    except OSError as error:
        raise LicenseValidationError("Failed to read license file.") from error

    return License.from_json(data)


def verify_license_signature(
    license: License,
    public_key_pem: bytes
) -> bool:
    payload_bytes = json.dumps(
        asdict(license.payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True
    ).encode("utf-8")

    try:
        signature_bytes = base64.b64decode(
            license.signature,
            validate=True
        )
    except (binascii.Error, ValueError):
        return False

    public_key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(public_key, ed25519.Ed25519PublicKey):
        raise TypeError("Expected an Ed25519 public key.")
        
    try:
        public_key.verify(signature_bytes, payload_bytes)
    except InvalidSignature:
        return False

    return True


def validate_license_payload(
    license_payload: LicensePayload,
    expected_machine_id: str
):
    if license_payload.version != SUPPORTED_LICENSE_VERSION:
        raise LicenseValidationError("Unsupported license version.")

    if license_payload.machine_id != expected_machine_id:
        raise LicenseValidationError("License is not valid for this machine.")

    try:
        expires_at = datetime.strptime(license_payload.expires_at, "%Y-%m-%d").date()
    except ValueError as error:
        raise LicenseValidationError("Invalid license date format.") from error

    if expires_at.isoformat() != license_payload.expires_at:
        raise LicenseValidationError("Invalid license date format.")

    utc_now = datetime.now(timezone.utc).date()
    if expires_at < utc_now:
        raise LicenseValidationError("License has expired.")


def validate_license(
    license_path: Path,
    expected_machine_id: str,
    public_key_pem: bytes
):
    license = load_license(license_path)

    if not verify_license_signature(license, public_key_pem):
        raise LicenseValidationError("Invalid license signature.")

    validate_license_payload(license.payload, expected_machine_id)
    
    check_license_clock(expected_machine_id)

