#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# parse args
action="${1:-reinstall}"

# resolve mascope path
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_PATH=$( dirname "$SCRIPT_DIR" )

# main procedure
function main() {
    write_intro

    if [ "$(action_in 'uninstall' 'reinstall')" ]; then
        uninstall_mascope_modules
        clear_mascope_envvars
    fi

    if [ "$(action_in 'install' 'reinstall')" ]; then
        set_mascope_envvars
        install_tooling
    fi

    if [ "$(action_in 'install' 'reinstall' 'update')" ]; then
        clear_mascope_state
        install_mascope_modules
    fi

    write_outro

    if [ "$(action_in 'install' 'reinstall')" ]; then
        su "${USER}"
    fi
}

function action_in() {
    for i in "${@}" ; do
        if [[ "$action" == "$i" ]]; then
            echo 0;
        fi
    done
}

function set_envvar() {
    # remove the old persisted value
    sudo sed -i "/${1}=/d" /etc/environment
    # set the new persisted value
    sudo bash -c "echo ${1}=${2} >> /etc/environment"
    # export variable to this script
    declare -gx "${1}=${2}"

    echo "Environment variable ${1} set to ${2}"
}

function set_mascope_envvars() {
    echo "

    +------------------------+
    | 📝 SETTING ENV VARS 📝 |
    +------------------------+

    "
    set_envvar 'MASCOPE_PATH' "${ROOT_PATH}"
}

function clear_mascope_envvars() {
    echo "

    +-------------------------+
    | 📝 CLEARING ENV VARS 📝 |
    +-------------------------+

    Removing all Mascope env vars from /etc/environment
    "
    sudo sed -i '/MASCOPE/d' /etc/environment
    declare -gx MASCOPE_PATH="${ROOT_PATH}"
}

function clear_mascope_state() {
    echo "

    +----------------------+
    | 🗑️ CLEARING STATE 🗑️ |
    +----------------------+

    Deleting runtime/state.json
    "
    rm "${ROOT_PATH}/runtime/state.json" || true
}

function install_tooling() {
    echo "

    +-------------------------+
    | 🐍 INSTALLING PYTHON 🐍 |
    +-------------------------+

    "
    if [[ -z $(command -v python3.12) ]]; then
            echo "

    Python 3.12 not detected; installing...

"
        # apt repos and update
        sudo add-apt-repository ppa:deadsnakes/ppa -y
        sudo add-apt-repository ppa:dotnet/backports -y
        sudo apt update

        # install python and dotnet runtime (for /libraries/mascope_hardware/orbitrap)
        sudo apt install -y python3.12 python3.12-venv dotnet-runtime-9.0
    else
        echo "

    Python 3.12 detected; skipping install.

"
    fi

    # install pipx
    python3.12 -m ensurepip --upgrade

    sudo apt install -y pipx
    pipx ensurepath
    # update PATH variable in this script's scope *
    declare -gx "PATH=${PATH}:/home/${USER}/.local/bin"
    #   * pipx adds a similar export to the user  ~/.bashrc
    #     but this requires a new terminal session. Without
    #     this, newly installed commands (like poetry) will
    #     not be found even if they are installed.

    # ensure pipx uses python 3.12
    python_path=$(which python3.12)
    if [[ PIPX_DEFAULT_PYTHON != "$python_path" ]]; then
        set_envvar 'PIPX_DEFAULT_PYTHON' "${python_path}"
    fi

    # install poetry to its own virtual env
    pipx install poetry

    echo "

    +-------------------------+
    | ☕ INSTALLING NODEJS ☕ |
    +-------------------------+

    "

    if [[ $(node -v) != v22* ]]; then
            echo "

    Node 22 not detected; installing...

"
        sudo apt-get install -y curl
        curl -fsSL https://deb.nodesource.com/setup_22.x -o nodesource_setup.sh
        sudo -E bash nodesource_setup.sh
        rm nodesource_setup.sh
        sudo apt-get install -y nodejs
    else
        echo "

    Node 22 detected; skipping install.

"
    fi

    # cli depedencency
    sudo npm install -g concurrently

    echo "

    +-------------------------+
    | 🐳 INSTALLING DOCKER 🐳 |
    +-------------------------+

    "
    if [[ -z $(command -v docker) ]]; then
        echo "

    Docker not detected; installing...

"
        sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
        sudo add-apt-repository -y "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
        apt-cache policy docker-ce
        sudo apt install -y docker-ce
        sudo usermod -aG docker "${USER}"
    else
        echo "

    Docker detected; skipping install.

"
    fi
}

function install_mascope_modules() {
    echo "

    +----------------------------------+
    | 🏗️ INSTALLING MASCOPE MODULES 🏗️ |
    +----------------------------------+

    "
    python3.12 ./setup/mascope.py install
}

function uninstall_mascope_modules() {
    echo "

    +------------------------------------+
    | 🏗️ UNINSTALLING MASCOPE MODULES 🏗️ |
    +------------------------------------+

    "
    python3.12 ./setup/mascope.py uninstall
}

function write_intro() {
    if [[ $action == 'install' ]]; then    
        echo "

    +-------------------------------+
    | 🚀 MASCOPE UBUNTU INSTALL  🚀 |
    +-------------------------------+

    Installing mascope modules

    "
    fi 
    if [[ $action == 'update' ]]; then
        echo "

    +-----------------------------+
    | 🚀 MASCOPE UBUNTU UPDATE 🚀 |
    +-----------------------------+

    Updating mascope modules
    "
    fi
    if [[ $action == 'uninstall' ]]; then
        echo "

    +--------------------------------+
    | 🚀 MASCOPE UBUNTU UNINSTALL 🚀 |
    +--------------------------------+

    Uninstalling mascope modules

    "
    fi
    if [[ $action == 'reinstall' ]]; then
        echo "

    +--------------------------------+
    | 🚀 MASCOPE UBUNTU REINSTALL 🚀 |
    +--------------------------------+

    Reinstalling mascope modules
    "
    fi
}


function write_outro() {
    if [[ $action == 'install' ]]; then    
        echo "

    +------------------------------------------+
    | 🎉 MASCOPE UBUNTU INSTALL SUCCESSFUL! 🎉 |
    +------------------------------------------+

    Logging you into a new terminal session to ensure access to
    the new command. Run 'mascope --help' and open the README.md 
    for documentation.
    "
    fi
    if [[ $action == 'update' ]]; then
        echo "

    +-----------------------------------------+
    | 🎉 MASCOPE UBUNTU UPDATE SUCCESSFUL! 🎉 |
    +-----------------------------------------+

    Run 'mascope --help' and open the README.md for documentation.
    "
    fi
    if [[ $action == 'uninstall' ]]; then
        echo "

    +--------------------------------------------+
    | 🎉 MASCOPE UBUNTU UNINSTALL SUCCESSFUL! 🎉 |
    +--------------------------------------------+

    "
    fi
    if [[ $action == 'reinstall' ]]; then
        echo "

    +--------------------------------------------+
    | 🎉 MASCOPE UBUNTU REINSTALL SUCCESSFUL! 🎉 |
    +--------------------------------------------+

    Logging you into a new terminal session to ensure access to
    the new command. Run 'mascope --help' and open the README.md 
    for documentation.
    "
    fi
}

main
