@echo off 

echo Build executable
call poetry run pyinstaller tof_agent.py --name bin --noconfirm --onefile --console --collect-all hardware.tofwerk --icon=assets/icon.ico
echo Executable published

copy scripts\install.cmd dist\
copy scripts\run.cmd dist\
copy tof_agent_config.yaml dist\

echo Make distribution package
tar.exe -a -c -f tof_agent.zip -C dist *
echo Find the distribution package in tof_agent.zip