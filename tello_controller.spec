a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('sounds/*.wav', 'sounds'),
        ('assets/*.png', 'assets'),
    ],
    hiddenimports=['djitellopy'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='TelloController',
    console=False,
    onefile=True,
    icon='assets/icon.ico',
)
