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

    write_section "MASCOPE ${action^^}"

    write_line "Launching setup script in '${action}' mode"

    if [ "$(action_in 'uninstall' 'reinstall')" ]; then
        uninstall_mascope
        clear_envvars
    fi

    if [ "$(action_in 'install' 'reinstall')" ]; then
        set_envvars
        install_tooling
    fi

    if [ "$(action_in 'install' 'reinstall')" ]; then
        clear_state
        install_mascope
    fi

    write_section "MASCOPE ${action^^} SUCCESSFUL!"

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

function set_envvars() {
    write_section "SETTING ENV VAR"

    set_envvar 'MASCOPE_PATH' "${ROOT_PATH}"
}

function clear_envvars() {
    write_section "CLEARING ENV VAR"
    
    write_line "Removing all Mascope env vars from /etc/environment"

    sudo sed -i '/MASCOPE/d' /etc/environment
    declare -gx MASCOPE_PATH="${ROOT_PATH}"
}

function clear_state() {
    write_section "CLEARING STATE"

    write_line "Deleting /.runtime/state.json"
    
    rm "${ROOT_PATH}/.runtime/state.json" || true
}

function install_tooling() {
    write_section "INSTALLING TOOLING"

    sudo apt update
    sudo apt install -y curl build-essential
    
    if [[ -z $(command -v uv) ]]; then
        write_line "uv not detected, installing..."
        
        sudo snap install --classic astral-uv
    else

        write_line "uv detected, skipping install."
    fi

    if [[ $(node -v) != v22* ]]; then
        write_line "Node 22 not detected, installing..."
        
        curl -fsSL https://deb.nodesource.com/setup_22.x -o nodesource_setup.sh
        sudo -E bash nodesource_setup.sh
        rm nodesource_setup.sh
        sudo apt-get install -y nodejs
    else
        write_line "Node 22 detected, skipping install."
    fi

    # use jemalloc to ensure no free() pointer errors
    write_line "installing jemalloc"
    sudo apt install --yes --no-install-recommends libjemalloc2
    set_envvar 'LD_PRELOAD' "/usr/lib/x86_64-linux-gnu/libjemalloc.so.2"
    
    if [[ -z $(command -v dotnet) ]]; then
        write_line "dotnet runtime not detected, installing..."

        wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
            && sudo dpkg -i packages-microsoft-prod.deb \
            && rm packages-microsoft-prod.deb \
            && sudo apt update \
            && sudo apt install -y dotnet-runtime-9.0
    else
        write_line "dotnet detected, skipping install."
    fi

    # cli depedencency
    sudo npm install -g concurrently

    if [[ -z $(command -v docker) ]]; then
        write_line "Docker not detected, installing..."
       
        sudo apt install -y apt-transport-https ca-certificates software-properties-common
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
        sudo add-apt-repository -y "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
        apt-cache policy docker-ce
        sudo apt install -y docker-ce
        sudo usermod -aG docker "${USER}"
    else
        write_line "Docker detected, skipping install."
    fi
}

function install_mascope() {
    write_section "INSTALLING MASCOPE BINARIES"

    uv tool install --force .
    uv tool update-shell
}

function uninstall_mascope() {
    write_section "UNINSTALLING MASCOPE BINARIES"

    uv tool uninstall --all
}

function write_section() {
    
    echo "

    [${1}]

    "
}

function write_line() {
    echo "
    ${1}
    "
}

main
