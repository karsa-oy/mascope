#!/bin/bash
# ================================================================
# Set up dev environment on Ubuntu 1804
#
set -eu -o pipefail

#set -x
#trap read debug

echo AAA Setting up dev environment

os_name=$(lsb_release -si)
os_version=$(echo $(cat /etc/os-release | grep '^VERSION_ID=') | cut -d '"' -f 2)

if [[ $os_name != "Ubuntu" || $os_version < "18" ]]; then
	echo AAA $0 is supposed to run on Ubuntu 18, while current one is ${os_name} ${os_version}
	exit 1
fi


function install_dev_prerequisites() {
    echo AAA Install needed packages
    sudo apt update
    sudo dpkg --add-architecture i386

    # VirtualBox workaround: reset network to make it connect to custom repos
    sudo netplan apply

    sudo apt install -y git-all unzip ntpdate xvfb
    sudo apt install -y cmake
    sudo apt install -y python3-tk python3-dev
    sudo apt install -y python3-pip
    sudo -H python3 -m pip install -U pip
#    sudo apt install -y docker.io

    # workaround OpenSSL bug TODO: check if needed
    sudo -H python3 -m pip uninstall -y pyOpenSSL cryptography
    sudo -H python3 -m pip install pyOpenSSL cryptography
}


function install_candies() {
    echo AAA Set Helsinki time zone
    sudo timedatectl set-timezone Europe/Helsinki
#    echo "Europe/Helsinki" | sudo tee /etc/timezone
#    sudo dpkg-reconfigure --frontend noninteractive tzdata

    echo AAA Install FI keyboard layout
    sudo apt install -y x11-xkb-utils
    sudo setxkbmap fi || true
    echo "setxkbmap fi" >> ~/.bashrc
}


function install_default_dev_env() {
  echo AAA install_default_dev_env placeholder:
  return 0
}


APPROOT=$(realpath $(dirname $(realpath $BASH_SOURCE)))
install_dev_prerequisites
install_candies
install_default_dev_env


echo 
echo AAA dev setup finished. 
echo 

exit 0
