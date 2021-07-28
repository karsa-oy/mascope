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

if [[ $os_name != "Ubuntu" || $os_version < "20" ]]; then
	echo AAA $0 is supposed to run on Ubuntu 20, while current one is ${os_name} ${os_version}
	exit 1
fi


function install_dev_prerequisites() {
    echo AAA Install needed packages
    sudo apt update
    sudo dpkg --add-architecture i386

    # VirtualBox workaround: reset network to make it connect to custom repos
    sudo netplan apply

    sudo apt install -y git-all unzip ntpdate xterm
    # sudo apt install -y xvfb
    sudo apt install -y cmake
    # sudo apt install -y python3-tk python3-dev python3-pip
    sudo apt install -y python3-pip python3.8-dev python3.8-distutils python3.8-venv
    sudo -H python3 -m pip install -U pip
    sudo -H python3 -m pip install pillow
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
    echo AAA install_default_dev_env:

    echo AAA create karsa shortcuts:
    ln -f -s /vagrant/src/run_services.sh /home/vagrant/Desktop/karsa_backend
    ln -f -s /vagrant/test/unit/run_unittests.sh /home/vagrant/Desktop/karsa_unittests
    ln -f -s /vagrant/test/system/run_unittests.sh /home/vagrant/Desktop/karsa_system_tests

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
