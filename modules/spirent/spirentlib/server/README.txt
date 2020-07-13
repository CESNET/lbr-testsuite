dependencies :
pywin32
pyinstaller

logy sa nachádzajú v súbore s cestou "C:\logger.log"

1) Vytvorenie SpirentServerCtrl.exe

pyinstaller -n "SpirentServerCtrl" -F --hidden-import=win32timezone windows_service.py

2) Inštalácia služby 

dist\SpirentServerCtrl.exe --startup=auto install

3) Spustenie služby

dist\SpirentServerCtrl.exe start

4) Zastavenie služby

dist\SpirentServerCtrl.exe stop

Vymazanie služby

dist\SpirentServerCtrl.exe remove