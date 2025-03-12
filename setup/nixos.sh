#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# parse args
action="${1:-reinstall}"

# main procedure
function main() {
    write_intro


    if [ "$(action_in 'uninstall' 'reinstall')" ]; then
        uninstall_mascope_modules
    fi

    if [ "$(action_in 'install' 'reinstall' 'update')" ]; then
        clear_mascope_state
        install_mascope_modules
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


function install_mascope_modules() {
    echo "

    +----------------------------------+
    | 🏗️ INSTALLING MASCOPE MODULES 🏗️ |
    +----------------------------------+

    "
    python3 ./setup/mascope.py install
}

function uninstall_mascope_modules() {
    echo "

    +------------------------------------+
    | 🏗️ UNINSTALLING MASCOPE MODULES 🏗️ |
    +------------------------------------+

    "
    python3 ./setup/mascope.py uninstall
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
