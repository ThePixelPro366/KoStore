# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('api', 'api'),
        ('services', 'services'),
        ('ui', 'ui'),
        ('utils', 'utils'),
        ('workers', 'workers'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngine',
        'requests',
        'utils.resource_paths',
        'utils.markdown',
        'ui.themes',
        'ui.plugin_card',
        'ui.loading_overlay',
        'ui.readme_text_edit',
        'ui.patch_selection_dialog',
        'api.github',
        'workers.download_worker',
        'services.device_detection',
        'services.plugin_installer',
        'services.cache',
        'services.update_service',
    ] + collect_submodules('PyQt6'),  # auto-collect any PyQt6 submodules
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Choose target_arch dynamically:
# In GitHub Actions, we can replace this value before build
# or create two .spec files: build-arm64.spec and build-x86_64.spec
target_arch = os.environ.get('PYINSTALLER_TARGET_ARCH', None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KOReader_Store',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch,  # set via environment variable in CI
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
