#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# parse args
action=$1
modules="${*:2}"

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

    if [ "$(action_in 'uninstall' 'reinstall')" ]; then
        uninstall_mascope_modules "${modules}"
        if [ $cli ]; then
            uninstall_mascope_cli
        fi
    fi

    if [ "$(action_in 'install' 'reinstall' 'update')" ]; then
        clear_mascope_state
        if [ $cli ]; then
            install_mascope_cli
        fi
        install_mascope_modules "${modules}"
    fi

    write_outro
}

function action_in() {
    for i in "${@}" ; do
        if [[ "$action" == "$i" ]]; then
            echo 0;
        fi
    done
}

function clear_mascope_state() {
    echo "

    +----------------------+
    | 🗑️ CLEARING STATE 🗑️ |
    +----------------------+

    Deleting runtime/state.json
    "
    rm "${MASCOPE_PATH}/runtime/state.json" || true
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
    poetry env use "${PIPX_DEFAULT_PYTHON}"
    poetry build
    # install for user
    pipx install .

    cd "${MASCOPE_PATH}"
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

    +------------------------------+
    | 🚀 MASCOPE NIXOS INSTALL  🚀 |
    +------------------------------+

    Installing mascope modules

    "
    fi 
    if [[ $action == 'update' ]]; then
        echo "

    +----------------------------+
    | 🚀 MASCOPE NIXOS UPDATE 🚀 |
    +----------------------------+

    Updating mascope modules
    "
    fi
    if [[ $action == 'uninstall' ]]; then
        echo "

    +-------------------------------+
    | 🚀 MASCOPE NIXOS UNINSTALL 🚀 |
    +-------------------------------+

    Uninstalling mascope modules

    "
    fi
    if [[ $action == 'reinstall' ]]; then
        echo "

    +-------------------------------+
    | 🚀 MASCOPE NIXOS REINSTALL 🚀 |
    +-------------------------------+

    Reinstalling mascope modules
    "
    fi
}


function write_outro() {
    if [[ $action == 'install' ]]; then    
        echo "

    +-----------------------------------------+
    | 🎉 MASCOPE NIXOS INSTALL SUCCESSFUL! 🎉 |
    +-----------------------------------------+

    Logging you into a new terminal session to ensure access to
    the new command. Run 'mascope --help' and open the README.md 
    for documentation.
    "
    fi
    if [[ $action == 'update' ]]; then
        echo "

    +----------------------------------------+
    | 🎉 MASCOPE NIXOS UPDATE SUCCESSFUL! 🎉 |
    +----------------------------------------+

    Run 'mascope --help' and open the README.md for documentation.
    "
    fi
    if [[ $action == 'uninstall' ]]; then
        echo "

    +-------------------------------------------+
    | 🎉 MASCOPE NIXOS UNINSTALL SUCCESSFUL! 🎉 |
    +-------------------------------------------+

    "
    fi
    if [[ $action == 'reinstall' ]]; then
        echo "

    +-------------------------------------------+
    | 🎉 MASCOPE NIXOS REINSTALL SUCCESSFUL! 🎉 |
    +-------------------------------------------+

    Logging you into a new terminal session to ensure access to
    the new command. Run 'mascope --help' and open the README.md 
    for documentation.
    "
    fi
}

main
