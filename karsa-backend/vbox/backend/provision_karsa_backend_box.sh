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

target_os_version="20"
if [[ $os_name != "Ubuntu" || $os_version < $target_os_version ]]; then
	echo AAA $0 is supposed to run on Ubuntu $target_os_version, while current one is ${os_name} ${os_version}
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
    python3 -m pip install --user pillow
#    sudo apt install -y docker.io

    # workaround OpenSSL bug TODO: check if needed
    sudo -H python3 -m pip uninstall -y pyOpenSSL cryptography || true
    python3 -m pip install --user pyOpenSSL cryptography
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
    ln -f -s /vagrant/ /home/vagrant/Desktop/backend_src || true
    ln -f -s /vagrant/run_services.sh /home/vagrant/Desktop/run_backend
    ln -f -s /vagrant/test/unit/run_unittests.sh /home/vagrant/Desktop/run_unittests
    ln -f -s /vagrant/test/system/run_unittests.sh /home/vagrant/Desktop/run_system_tests

    echo AAA copy data for system tests
    rm -rf /home/vagrant/TofDaq
    rm -rf /home/vagrant/Projects
    cp -r -f /vagrant/test/system/TestData/* /home/vagrant/
    for dt in /home/vagrant/TofDaq/*; do
        for dn in $dt/*; do
            fn=$(basename $dn)
            ln -f -s $dn /home/vagrant/Projects/LinuxProject/Experiment_1/$fn
        done
    done

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
