

Windows CMD Command:
```
@echo off
setlocal enabledelayedexpansion

echo Checking current directory...

:: Get script name
for %%F in ("%~nx0") do set "SCRIPT_NAME=%%~nxF"

:: Count files excluding this script
set "FILE_COUNT=0"
for %%F in (*) do (
    if not "%%~nxF"=="%SCRIPT_NAME%" set /a "FILE_COUNT+=1"
)

:: Check if directory has other files and no rcc.exe
if %FILE_COUNT% GTR 0 (
    if not exist "rcc.exe" (
        echo Directory is not empty and does not contain rcc.exe. Stopping execution.
        exit /b 1
    )
)

echo Checking if RCC exists...
if exist "rcc.exe" (
    echo RCC executable already exists. Skipping download.
) else (
    echo Downloading RCC executable...
    curl -o rcc.exe https://downloads.robocorp.com/rcc/releases/v17.18.0/windows64/rcc.exe
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to download RCC executable.
        exit /b 1
    )
    echo RCC downloaded successfully.
)
echo Pulling repository from GitHub...
rcc.exe pull github.com/MaxWindt/audio_silence_splitter
echo Running the tool...
rcc.exe run
echo Process completed.
```

Mac Shell Command:
```
#!/bin/bash

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found!"
    exit 1
fi

# Create run script only if it doesn't exist
if [ ! -f "run.sh" ]; then
    echo "Creating run script..."
    echo '#!/bin/bash
source .venv/bin/activate
python main.py' > run.sh
    chmod +x run.sh
fi

echo "Installation complete. Run with: ./run.sh"
```
