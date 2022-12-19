#!/bin/bash
# ================================================================
# Set up dev environment on Ubuntu 1804
#
set -eu -o pipefail

#set -x
#trap read debug

echo AAA Setting up environment

os_name=$(lsb_release -si)
os_version=$(echo $(cat /etc/os-release | grep '^VERSION_ID=') | cut -d '"' -f 2)

if [[ $os_name != "Ubuntu" || $os_version < "18" ]]; then
	echo AAA $0 is supposed to run on Ubuntu 18 or newer, while current one is ${os_name} ${os_version}
	exit 1
fi


function install_prerequisites() {
    echo AAA Install needed packages
    sudo apt-get update
    sudo apt install -y python3-pip patchelf
    sudo apt-get install -y mono-complete
    echo $PATH | grep ~/.local/bin: || echo "export PATH=\"$HOME/.local/bin:$PATH\"" >> ~/.bashrc
    echo $PATH | grep ~/.local/bin: || export PATH="$HOME/.local/bin:$PATH"

    echo AAA setting up mascope backend

    source $MY_PATH/.env
    pip install --upgrade $MY_PATH/backend*.whl
    cp -rf $MY_PATH/config/* $MASCOPE_PRIVATE_CONFIG_DIR
    chmod +x $MY_PATH/mascope-run-backend
    cp -f $MY_PATH/mascope-run-backend ~/.local/bin
    cp -f $MY_PATH/.env ~/.local/bin
    USER_SITE_PACKAGES=$(python3 -m site --user-site)
    TWLIBPATH=$USER_SITE_PACKAGES/hardware/tofwerk/lib/dlls/linux_x86_64/
    patchelf --force-rpath --set-rpath "$TWLIBPATH" "$TWLIBPATH/libtwh5.so"
}


function install_candies() {
    echo AAA Set Helsinki time zone
    sudo timedatectl set-timezone Europe/Helsinki
    # echo "Europe/Helsinki" | sudo tee /etc/timezone
    # sudo dpkg-reconfigure --frontend noninteractive tzdata

    echo AAA Install FI keyboard layout
    # sudo apt install -y x11-xkb-utils
    # sudo setxkbmap fi || true
    # echo "setxkbmap fi\n" >> ~/.bashrc
    sudo loadkeys fi
}


function install_default_dev_env() {
  echo AAA install_default_dev_env placeholder:
  return 0
}


MY_PATH=$(realpath $(dirname $(realpath $BASH_SOURCE)))
# MASCOPE_UI=$(realpath $(dirname $MY_PATH))
# MASCOPE_PROJECT=$(realpath $MY_PATH/../..)

install_candies
install_prerequisites
install_default_dev_env

echo 
echo AAA setup finished. 
echo 

exit 0
