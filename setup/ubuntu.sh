#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# parse args
action=$1
modules="${@:2}"

# resolve mascope path
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_PATH=$( dirname $SCRIPT_DIR )

# determine wheter or not the CLI
# should be un/re/installed:
if [[ $modules == *cli* ]]; then
    cli=1
elif [[ -z $modules ]]; then
    cli=1
else
    cli=0
fi

# main procedure
function main() {
    write_intro

    if [ $(action_in "uninstall" "reinstall") ]; then
        uninstall_mascope_modules "${modules}"
        if [ $cli ]; then
            uninstall_mascope_cli
        fi
        clear_mascope_envvars
    fi

    if [ $(action_in "install" "reinstall") ]; then
        set_mascope_envvars
        install_tooling
    fi

    if [ $(action_in "install" "reinstall" "update") ]; then
        clear_mascope_state
        if [ $cli ]; then
            install_mascope_cli
        fi
        install_mascope_modules "${modules}"
    fi

    write_outro

    if [ $(action_in "install" "reinstall") ]; then
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
        sudo apt update

        # install python
        sudo apt install -y python3.12 python3.12-venv
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
    if [[ PIPX_DEFAULT_PYTHON != $python_path ]]; then
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
        sudo usermod -aG docker ${USER}
    else
        echo "

    Docker detected; skipping install.

"
    fi
}

function install_mascope_cli() {
    echo "

    +------------------------------+
    | ⚡ INSTALLING MASCOPE CLI ⚡ |
    +------------------------------+

    "
    cd "${MASCOPE_PATH}/runtime/cli"

    # try to uninstall, ignore failure
    pipx uninstall mascope_cli || true
    # build with poetry
    poetry env use $PIPX_DEFAULT_PYTHON
    poetry build
    # install for user
    pipx install .

    cd ${MASCOPE_PATH}
}

function uninstall_mascope_cli() {
    echo "

    +--------------------------------+
    | ⚡ UNINSTALLING MASCOPE CLI ⚡ |
    +--------------------------------+

    "
    cd "${MASCOPE_PATH}/runtime/cli"

    # try to uninstall, ignore failure
    pipx uninstall mascope_cli || true
    # remove all virtual envs
    poetry env remove --all

    cd "${MASCOPE_PATH}"
}

function install_mascope_modules() {
    echo "

    +----------------------------------+
    | 🏗️ INSTALLING MASCOPE MODULES 🏗️ |
    +----------------------------------+

    "
    mascope dev install $1
}

function uninstall_mascope_modules() {
    echo "

    +------------------------------------+
    | 🏗️ UNINSTALLING MASCOPE MODULES 🏗️ |
    +------------------------------------+

    "
    mascope dev uninstall $1
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
