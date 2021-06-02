REM Build PIVageant bin package release

@echo off

PUSHD .

CD ..

RMDIR /S /Q dist
RMDIR /S /Q build

"%UserProfile%\AppData\Local\Programs\Python\Python38\python.exe" -O -m PyInstaller .\package\PIVageant-bld.spec
"%UserProfile%\AppData\Local\Programs\Python\Python38\python.exe" -O -m PyInstaller .\package\Genkeys-bld.spec

POPD

PAUSE
