REM Build PIVageant bin package release

@echo off

PUSHD .

CD ..

RMDIR /S /Q dist
RMDIR /S /Q build
RMDIR /S /Q pivenv


SET PYINSTALLER_VER=4.5.1

REM Detect if run in Github Action
IF "%GITHUB_ACTION%"=="" (
  REM Building in a standard machine
  SET python_bin="%UserProfile%\AppData\Local\Programs\Python\Python39\python.exe"
  SET pyinst_dest="C:\pyinstaller_src"
) ELSE (
  REM Building in a Github Action VM
  SET python_bin="python"
  SET pyinst_dest=%HOME%
)

SET python_env="pivenv\Scripts\python"

echo Preparing environment and dependencies
%python_bin% -m venv pivenv
%python_env% -m pip install -U pip
%python_env% -m pip install wheel
%python_env% -m pip install wxPython==4.1.1
%python_env% setup.py install

echo Getting PyInstaller source
%python_env% package/get-pyinst-src.py %PYINSTALLER_VER%
REM Unzip source at C: root as a workaround to pyinstaller issue #4824
%python_env% -m zipfile -e pyinstaller-%PYINSTALLER_VER%.zip %pyinst_dest%\
echo Compile the bootloader
SET INSTALLDIR=%cd%
cd %pyinst_dest%\pyinstaller-%PYINSTALLER_VER%
del PyInstaller\bootloader\Windows-64bit\*.exe
cd bootloader
%INSTALLDIR%\%python_env% waf distclean
%INSTALLDIR%\%python_env% waf --target-arch 64bit all
cd ..
echo Installing PyInstaller %PYINSTALLER_VER%
%INSTALLDIR%\%python_env% setup.py install

echo Packaging PIVageant
cd %INSTALLDIR%
%python_env% -O -m PyInstaller .\package\PIVageant-bld.spec

POPD
echo Compilation done.
echo Binary result is in the dist folder.
