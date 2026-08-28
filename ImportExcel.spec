# -*- mode: python ; coding: utf-8 -*-
from importlib.util import find_spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

mssql_python_spec = find_spec("mssql_python")
if mssql_python_spec is None or mssql_python_spec.origin is None:
    raise RuntimeError("Package 'mssql_python' is not installed.")

mssql_python_path = Path(mssql_python_spec.origin).parent
ddbc_bindings = list(mssql_python_path.glob("ddbc_bindings*.pyd"))

if len(ddbc_bindings) != 1:
    raise RuntimeError(
        f"Expected exactly one ddbc_bindings binary, found {len(ddbc_bindings)}."
    )

datas = []
binaries = [(str(ddbc_bindings[0]), "mssql_python")]
hiddenimports = []
tmp_ret = collect_all('mssql_python')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('mssql_python_odbc')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['src/import_excel.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ImportExcel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
