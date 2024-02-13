# File mover agent

File mover agent monitors the contents of a _source_ directory, and when a new file appears, it starts to poll the filesize. After the filesize remains unchanged, it moves it into the _target_ directory.

### NOTE: The application is at a premature state, and not under active development. It is left here mainly for future reference.

### Description

```
mascope
├───agents           # Agent applications
│   ├───file_mover       # File mover
│   │   ├───assets          # Icon
│   │   ├───scripts         # Build script
│   │   └───file_mover.py   # Main program
│   ├───ht300a
│   └───tof_agent
├───backend
├───frontend
└───scripts
```

### Development

1. `poetry install`
2. `poetry run python file_mover.py`
3. (See available command line arguments by running `poetry run python file_mover.py --help`)
