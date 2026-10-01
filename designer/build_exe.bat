@echo off
rem Baut S51-Designer.exe (Windows). Ergebnis: designer\dist\S51-Designer.exe
cd /d "%~dp0"
python -m pip install pyinstaller==6.10.0 pillow==11.0.0 || goto fehler
python -m PyInstaller --noconfirm --onefile --windowed --name S51-Designer --paths . S51-Designer.pyw || goto fehler
echo.
echo Fertig: dist\S51-Designer.exe
pause
exit /b 0
:fehler
echo.
echo Fehler beim Bauen. Ist Python installiert und im PATH?
pause
exit /b 1
