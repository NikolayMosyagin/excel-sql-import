import sys
import hashlib


def read_machine_guid() -> str:
    if sys.platform != "win32":
        raise OSError("Machine ID is supported only on Windows.")
    
    import winreg

    registry_path = r"SOFTWARE\Microsoft\Cryptography"

    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        registry_path,
        0,
        winreg.KEY_READ | winreg.KEY_WOW64_64KEY
    ) as key:
        value, value_type = winreg.QueryValueEx(key, "MachineGuid")

    if value_type != winreg.REG_SZ or not isinstance(value, str):
        raise ValueError("Windows MachineGuid must be a string.")

    return value


def get_machine_id() -> str:
    machine_guid = read_machine_guid()

    if not machine_guid:
        raise ValueError("Windows MachineGuid cannot be empty.")

    source = f"ImportExcel:v1:{machine_guid}"

    return hashlib.sha256(source.encode("utf-8")).hexdigest()