@echo off

taskkill /F /T /FI "WINDOWTITLE eq mascope-tof-agent*"
start "mascope-tof-agent" cmd /k bin --config tof_agent_config.yaml