@echo off
rem Sistema de Comprobantes - version arreglada (corre el launcher desde el codigo fuente)
set RESOURCE_DIR=C:\Users\marko\AppData\Local\SistemaComprobantes
cd /d C:\Users\marko\comprobantesvm-src
start "" "C:\Users\marko\AppData\Local\Programs\Python\Python312\pythonw.exe" launcher.py
