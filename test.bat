@echo off
setlocal enabledelayedexpansion
set "script_path=%~dp0"
set filename=%1
call python3 "%script_path%\clean_demod_data.py" -txt "%filename%"
echo Hex is Made
set "foundFile="
for %%F in ("%script_path%\*_output.txt") do (
    set foundFile=%%~nxF
)

for %%i in ("%script_path%*.txt") do (
    if not "%script_path%!foundFile!" == "%%i" (
        for /f "usebackq tokens=*" %%j in ("%%i") do (
           call python3 "%script_path%beacon_parser.py" -x "%%j" >> "%script_path%\!foundFile!"
        )
    )
)
echo "%script_path%beacon_to_csv_custom.py"
call python3 "%script_path%beacon_to_csv_custom.py" -csv "___beacon" -txt "%script_path%!foundFile!"
call python3 get_up_time.py
call python3 get_reset_count.py

del /Q "%script_path%*.txt"
del /Q "%script_path%*.csv"
