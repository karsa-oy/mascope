### Description 
This project contains the Mascope backend, written in Python.

### Setup Requirements 
* python >=3.8, <3.11
* poetry >= 1.0.0


### Project setup with Poetry

This project uses [Poetry](https://python-poetry.org/); Poetry is an all-in-one Python project management tool. Poetry manages dependencies and project settings (via a modern `pyproject.toml` file. It supports dependency locking via a `poetry.lock` file which pins the versions of all dependencies in the tree; **the `poetry.lock` file should be comitted in the repository and updated correctly whenever our dependencies change**. It also manages Python virtual environments for you.

Once you have Poetry installed, you can run the following commands in this folder:
 * `poetry shell` to enter a development shell
 * `poetry install` to install the code into a virtual env managed by poetry
 * `poetry run` will run the virtual environment
 * `poetry run <script-name>` to run a script; we have the following:
   - `router`
   - `visualization-service`
   - `file-streaming-service`
   - `file-io-service`
   - `sample-service`
   - `signal-service`
   - `target-service`

To manage dependencies:
  * `poetry add/remove` to add or remove packages
  * `poetry lock` will update the `poetry.lock` file;


### Project setup with Docker

See the README at the monorepo root.

### Project setup with VirtualBox and Vagrant

1) Have VirtualBox and vagrant installed

2) go to vbox\backend folder

cd vbox\backend

1) run development setup for the project in VirtualBox virtual environment

vagrant up


### Project profiling

1) py-spy profiler comes along with dev.setup: https://github.com/benfred/py-spy

py-spy record -o profile.svg --pid 12345


### Project testing

#### Unit testing

1) Unittests are located in test/unit directory

test\unit\run_unittests.cmd

### Compile and build distribution packages

1) from each service folder, run build.cmd: find .whl release package in dist folder

2) use pip to install release package locally
