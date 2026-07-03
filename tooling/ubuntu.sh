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
    sudo apt install -y curl build-essential python3-dev pkg-config
    
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
    
    # configure Redis memory overcommit for background saves
    write_line "configuring Redis memory overcommit"
    if ! grep -q "vm.overcommit_memory" /etc/sysctl.conf; then
        sudo bash -c "echo 'vm.overcommit_memory = 1' >> /etc/sysctl.conf"
        sudo sysctl -p
        write_line "Redis memory overcommit enabled (vm.overcommit_memory = 1)"
    else
        write_line "Redis memory overcommit already configured, skipping."
    fi

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
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /tmp/docker.asc
        sudo cp /tmp/docker.asc /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        rm /tmp/docker.asc
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" \
            | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
        sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        sudo usermod -aG docker "${USER}"
    else
        write_line "Docker detected, skipping install."
    fi
}

function install_mascope() {
    write_section "INSTALLING MASCOPE BINARIES"

    # Force C17 standard to avoid GCC 15+ / C23 incompatibilities with
    # native extensions (e.g. numcodecs blosc typedef bool).
    # Pin Python 3.12 so uv downloads a managed interpreter matching
    # the project's requires-python constraint (<3.13).
    # --reinstall (implies --refresh) forces a rebuild from source: every
    # mascope package is pinned to version 0.0.0 (the real version is derived
    # from git at runtime), so uv's cache cannot tell releases apart and would
    # otherwise reuse a stale wheel - silently shipping old CLI code after an
    # update to a new release.
    CFLAGS="-std=c17" uv tool install --force --reinstall --python 3.12 .
    uv tool update-shell

    write_section "ENABLING SYSTEMD SERVICE"

    MASCOPE_BIN=$(command -v mascope)
    if [[ -z "${MASCOPE_BIN}" ]]; then
        write_line "ERROR: mascope binary not found on PATH after install"
        exit 1
    fi

    sed -e "s|@@USER@@|${USER}|g" \
        -e "s|@@MASCOPE_BIN@@|${MASCOPE_BIN}|g" \
        "${ROOT_PATH}/tooling/mascope.service" \
        | sudo tee /etc/systemd/system/mascope.service > /dev/null

    sudo systemctl daemon-reload
    sudo systemctl enable mascope.service
    write_line "mascope.service enabled for user '${USER}' (bin: ${MASCOPE_BIN})"
}

function uninstall_mascope() {
    write_section "DISABLING SYSTEMD SERVICE"

    sudo systemctl stop mascope.service || true
    sudo systemctl disable mascope.service || true
    sudo rm -f /etc/systemd/system/mascope.service
    sudo systemctl daemon-reload
    write_line "mascope.service disabled and removed"

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
