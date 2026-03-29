# -*- mode: python ; coding: utf-8 -*-
# AD BioGuard — PyInstaller spec

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=collect_dynamic_libs('webview'),
    datas=[
        ('ui/index.html',   'ui'),
        ('ui/overlay.html', 'ui'),
        ('ui/style.css',    'ui'),
        ('ui/app.js',       'ui'),
        *collect_data_files('webview'),
    ],
    hiddenimports=[
        'webview',
        'webview.platforms.winforms',
        'clr',
        'win32gui',
        'win32ts',
        'win32con',
        'win32api',
        'pywintypes',
        'keyboard',
        'cv2',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BioGuard',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    uac_admin=True,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='BioGuard',
)
