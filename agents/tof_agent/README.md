# Tofwerk TOF agent

### Description

Application for interacting with time-of-flight (TOF) mass spectrometers manufactured by Tofwerk, using their proprietary TofDaq API.

```
mascope
├───agents                  # Agent applications
│   ├───file_mover
│   ├───ht300a
│   └───tof_agent                # TOF agent
│       ├───assets                  # Icon
│       ├───scripts                 # Scripts
│       ├───tof_agent_config.yaml   # Configuration file
│       └───tof_agent.py            # Main program
├───backend
├───frontend
└───scripts
```

### Development

1. `poetry install`
2. Edit the config file `tof_agent_config.yaml` according to the specific setup.
3. `poetry run tof-agent`
4. (See available command line arguments by running `poetry run tof-agent --help`)

### Deployment

1. Run `/scripts/build.cmd` from the root directory of the agent.
2. Deliver the resulted zip archive onto the target PC.
3. Extract the zip archive into a reasonable location.
4. Edit the config file `tof_agent_config.yaml` according to the specific setup.
5. Run the `install.cmd` batch script.
6. Launch TOF agent from the desktop shortcut.
7. (Add TOF agent to Windows startup applications.)
