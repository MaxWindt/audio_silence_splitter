

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

# Get the name of this script
SCRIPT_NAME=$(basename "$0")

echo "Checking current directory..."

# Check if directory is not empty (excluding hidden files and this script)
FILE_COUNT=$(ls -A | grep -v "^\." | grep -v "^$SCRIPT_NAME$" | wc -l)
if [ "$FILE_COUNT" -gt 0 ] && [ ! -f "rcc" ]; then
    echo "Directory is not empty and does not contain rcc. Stopping execution."
    exit 1
fi

echo "Checking if RCC exists..."
if [ -f "rcc" ]; then
    echo "RCC executable already exists. Skipping download."
else
    echo "Downloading RCC executable..."
    
    # Detect OS and download appropriate version
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        curl -o rcc https://downloads.robocorp.com/rcc/releases/v17.18.0/macos64/rcc
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -o rcc https://downloads.robocorp.com/rcc/releases/v17.18.0/linux64/rcc
    else
        echo "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    # Check if download was successful
    if [ $? -ne 0 ]; then
        echo "Failed to download RCC executable."
        exit 1
    fi
    
    # Make it executable
    chmod +x rcc
    echo "RCC downloaded successfully."
fi

# Make sure rcc is executable (in case it exists but isn't executable)
chmod +x rcc

echo "Pulling repository from GitHub..."
./rcc pull github.com/MaxWindt/audio_silence_splitter
echo "Running the tool..."
./rcc run
echo "Process completed." 
```
