@echo off
echo ========================================
echo Python 3.12 Environment Setup
echo ========================================

echo.
echo [Step 1] Checking Python 3.12 availability...
py -3.12 --version
if %errorlevel% neq 0 (
    echo ERROR: Python 3.12 is not installed!
    echo Please install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [Step 2] Creating virtual environment 'myenv312'...
if exist myenv312 (
    echo WARNING: myenv312 already exists. Deleting...
    rmdir /s /q myenv312
)
py -3.12 -m venv myenv312
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment!
    pause
    exit /b 1
)

echo.
echo [Step 3] Activating virtual environment...
call myenv312\Scripts\activate.bat

echo.
echo [Step 4] Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel
if %errorlevel% neq 0 (
    echo WARNING: Failed to upgrade some packages, but continuing...
)

echo.
echo [Step 5] Checking for requirements.txt...
if exist requirements.txt (
    echo Found requirements.txt, installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo WARNING: Some packages failed to install!
    )
) else (
    echo No requirements.txt found, skipping dependency installation.
)

echo.
echo [Step 6] Verification...
echo ========================================
echo Python version:
python --version
echo.
echo Python executable path:
where python
echo.
echo Pip version:
pip --version
echo ========================================

echo.
echo [SUCCESS] Python 3.12 environment setup complete!
echo.
echo To activate this environment in the future, run:
echo   myenv312\Scripts\activate.bat
echo.
pause
