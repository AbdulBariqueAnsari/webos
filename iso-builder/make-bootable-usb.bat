@echo off
setlocal enabledelayedexpansion

title Web OS v1.0 - Bootable USB Creator

echo ================================================
echo    Web OS v1.0 Ultimate - USB Bootable
echo    ISO ko pendrive mein dalna ka tarika
echo ================================================
echo.
echo   Yeh script:
echo   - ISO file automatically Desktop mein dhundhegi
echo   - Rufus download page kholegi
echo   - Step-by-step guide degi
echo.
echo   Nahin chahiye? Sirf Rufus guide chahiye?
echo   Direct: https://rufus.ie
echo.

:: ─── Find ISO automatically ──────────────────────
set "ISO_FILE="
if exist "%USERPROFILE%\Desktop\web-os-*.iso" (
    for %%f in ("%USERPROFILE%\Desktop\web-os-*.iso") do set "ISO_FILE=%%f"
)
if exist "%USERPROFILE%\Downloads\web-os-*.iso" (
    for %%f in ("%USERPROFILE%\Downloads\web-os-*.iso") do set "ISO_FILE=%%f"
)
if exist "%~dp0..\dist\*.iso" (
    for %%f in ("%~dp0..\dist\*.iso") do set "ISO_FILE=%%f"
)

if defined ISO_FILE (
    echo [FOUND] ISO mil gaya: !ISO_FILE!
    echo.
) else (
    echo [NOT FOUND] Desktop ya Downloads mein ISO nahi mila
    echo.
    set /p ISO_FILE="Enter ISO path (ya Enter daba kar Rufus direct kholein): "
    if "!ISO_FILE!"=="" (
        echo.
        echo [OK] Rufus download page khul raha hai...
        start https://rufus.ie
        echo.
        pause
        exit /b 0
    )
    if not exist "!ISO_FILE!" (
        echo [ERROR] File nahi mili: !ISO_FILE!
        pause
        exit /b 1
    )
)

:: ─── Show USB drives ─────────────────────────────
echo Available drives (removable check):
wmic logicaldisk get deviceid,drivetype,volumename 2>nul | findstr "^[A-Z]" >nul
echo.
echo   Drive Type Legend: 2=Removable(USB), 3=Local
for /f "skip=1 tokens=1-3" %%a in ('wmic logicaldisk get deviceid^,drivetype^,volumename 2^>nul') do (
    if not "%%a"=="" (
        set "dtype=%%b"
        if "!dtype!"=="2" (set "desc=USB") else (set "desc=HDD")
        if "%%c"=="" (set "vol=NO_LABEL") else (set "vol=%%c")
        echo   %%a [!desc!] !vol!
    )
)
echo.
echo   NOTE: Direct write nahi karega, Rufus recommend karte hain
echo   (Rufus safely handle karta hai USB writing)

:: ─── Instructions ────────────────────────────────
echo.
echo ================================================
echo   RUFUS SE USB MEIN ISO DALNE KA TARIKA
echo ================================================
echo.
echo   Step 1: Rufus download karein (agar nahi hai)
echo          https://rufus.ie
echo.
echo   Step 2: Rufus open karein (admin rights dein)
echo.
echo   Step 3: USB drive select karein (8GB+)
echo.
echo   Step 4: "SELECT" par click karke ISO choose karein:
echo          !ISO_FILE!
echo.
echo   Step 5: Partition scheme:
echo          - GPT (UEFI mode) - naye PC/laptop ke liye
echo          - MBR (Legacy BIOS) - purane PC ke liye
echo.
echo   Step 6: "START" dabayein
echo          - Warning ayega - OK dabayein
echo          - "DD Image mode" poochhe to HA karein
echo.
echo   Step 7: Complete hone tak wait karein
echo          (5-10 minutes lagte hain)
echo.
echo   === BOOT KAISE KAREIN ===
echo.
echo   Step 8: USB nikal kar target PC mein laga dein
echo.
echo   Step 9: PC restart karein
echo          Boot menu key repeatedly dabayein:
echo          F12 / F2 / Del / Esc (brand par depend karta hai)
echo.
echo   Step 10: USB drive select karein
echo.
echo   Step 11: GRUB menu dikhega:
echo           - "Web OS v1.0 Ultimate - Boot Live"
echo             (try karne ke liye - install nahi hoga)
echo           - "Web OS v1.0 Ultimate - Install to Hard Drive"
echo             (permanently install karne ke liye)
echo.
echo   Step 12: Boot hone ke baad:
echo           - Local display par Web OS desktop dikhega
echo           - Ya browser mein: http://localhost:8080
echo           - Login: admin / admin
echo.
echo ================================================
echo.

start https://rufus.ie
echo [OK] Rufus download page khul gaya - browser check karein
echo.
echo   Rufus already installed hai? to direct use karein
echo   Nahi hai? to page se download karein
echo.
echo   Koi problem? Rufus alternatives:
echo   - BalenaEtcher: https://www.balena.io/etcher/
echo   - Ventoy: https://www.ventoy.net
echo.
pause
