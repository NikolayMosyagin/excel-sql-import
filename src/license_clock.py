import win32event
import win32api
import win32crypt
from win32cryptcon import (CRYPTPROTECT_LOCAL_MACHINE, CRYPTPROTECT_UI_FORBIDDEN)
import winreg
from datetime import datetime, timezone, timedelta
import json
import pywintypes

from src.license_clock_state import LicenseClockState
from src.exceptions import LicenseClockStateSaveError, LicenseValidationError


def check_license_clock(machine_id: str) -> None:
    mutex_name = "Global\\ImportExcel_LicenseState"
    mutex = None


    acquired = False
    
    try:
        try:
            mutex = win32event.CreateMutex(None, False, mutex_name)
            result = win32event.WaitForSingleObject(mutex, 10000)
        except pywintypes.error as error:
            raise LicenseValidationError("Failed to acquire license clock mutex.") from error

        if result == win32event.WAIT_TIMEOUT:
            raise LicenseValidationError("Timed out waiting for license clock mutex.")

        if result not in (win32event.WAIT_ABANDONED, win32event.WAIT_OBJECT_0):
            raise LicenseValidationError(f"Unexpected mutex wait result: {result}.")

        acquired = True
        now = datetime.now(timezone.utc)

        state = load_clock_state()

        if (state is not None):
            validate_clock_state(state, machine_id, now)

        new_state = LicenseClockState(
            version=1,
            machine_id=machine_id,
            last_run_utc=max(now, state.last_run_utc if state is not None else now)
        )

        save_clock_state(new_state)
    finally:
        if mutex is not None:
            try:
                if acquired:
                    win32event.ReleaseMutex(mutex)
            finally:
                win32api.CloseHandle(mutex)


def load_clock_state() -> LicenseClockState | None:
    registry_path = r"Software\ImportExcel"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            value, value_type = winreg.QueryValueEx(key, "LicenseState")
    except FileNotFoundError:
        return None
    except OSError as error:
        raise LicenseValidationError("Failed to read license clock state from registry.") from error

    if value_type != winreg.REG_BINARY or not isinstance(value, bytes):
        raise LicenseValidationError("Invalid license clock state format.")

    try:
        _, decrypted_bytes = win32crypt.CryptUnprotectData(
            value,
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN
        )
    except pywintypes.error as error:
        raise LicenseValidationError("Failed to decrypt license clock state.") from error
    
    try:
        data = json.loads(decrypted_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LicenseValidationError("Invalid license clock state JSON.") from error
    
    return LicenseClockState.from_dict(data)


def save_clock_state(state: LicenseClockState) -> None:
    registry_path = r"Software\ImportExcel"
    
    state_bytes = json.dumps(
        state.to_dict(), 
        ensure_ascii=False, 
        sort_keys=True, 
        separators=(",", ":")
    ).encode("utf-8")

    try:
        protect_bytes = win32crypt.CryptProtectData(
            state_bytes,
            "ImportExcel License State",
            None,
            None,
            None,
            CRYPTPROTECT_LOCAL_MACHINE | CRYPTPROTECT_UI_FORBIDDEN
        )
    except pywintypes.error as error:
        raise LicenseValidationError("Failed to encrypt license clock state.") from error
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, registry_path) as key:
            winreg.SetValueEx(key, "LicenseState", 0, winreg.REG_BINARY, protect_bytes)
    except OSError as error:
        raise LicenseClockStateSaveError("Failed to write license clock state to registry.") from error


def validate_clock_state(
    state: LicenseClockState,
    machine_id: str,
    now: datetime
) -> None:
    if state.version != 1:
        raise LicenseValidationError(
            f"Unsupported license clock state version: {state.version}."
        )

    if state.machine_id != machine_id:
        raise LicenseValidationError(
            "License clock state machine ID mismatch."
        )

    if now + timedelta(minutes=5) < state.last_run_utc:
        raise LicenseValidationError(
            "System clock rollback detected."
        )