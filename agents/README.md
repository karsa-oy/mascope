# Agents

### Description

This directory contains Mascope peripheral agent applications, written in Python. The agents are standalone applications, i.e. they are run on their own Python interpreter. Therefore each agent also has their own poetry environment configuration, and must be installed separately using `poetry install` inside their respective directory. For more details on a particular agent, refer to their respective README.

```
mascope
├───agents           # Agent applications
│   ├───file_mover      # File mover
│   ├───ht300a          # Autosampler
│   └───tof_agent       # Tofwerk TOF
├───backend
├───frontend
└───scripts
```
