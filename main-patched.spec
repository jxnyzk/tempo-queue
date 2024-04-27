# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['dist\\obf\\temp'],
    binaries=[],
    datas=[('templates/*', 'templates')],
    hiddenimports=['pytransform'],
    hookspath=['dist\\obf\\temp'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# Patched by PyArmor
_src = 'C:\\Users\\Andrei\\Desktop\\TQueueBot'
_obf = 0
for i in range(len(a.scripts)):
    if a.scripts[i][1].startswith(_src):
        x = a.scripts[i][1].replace(_src, r'C:\Users\Andrei\Desktop\TQueueBot\dist\obf')
        if os.path.exists(x):
            a.scripts[i] = a.scripts[i][0], x, a.scripts[i][2]
            _obf += 1
if _obf == 0:
    raise RuntimeError('No obfuscated script found')
for i in range(len(a.pure)):
    if a.pure[i][1].startswith(_src):
        x = a.pure[i][1].replace(_src, r'C:\Users\Andrei\Desktop\TQueueBot\dist\obf')
        if os.path.exists(x):
            if hasattr(a.pure, '_code_cache'):
                with open(x) as f:
                    a.pure._code_cache[a.pure[i][0]] = compile(f.read(), a.pure[i][1], 'exec')
            a.pure[i] = a.pure[i][0], x, a.pure[i][2]
# Patch end.

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
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
