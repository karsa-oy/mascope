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
    sudo apt-get install -y nginx

    # echo AAA setting up mascope backend

    # use production .env
    source $MY_PATH/.env

    echo AAA setting up mascope frontend...

    rm -r -f $MASCOPE_UI || true
    mv -f $MY_PATH/dist $MASCOPE_UI
    # create mascope db link
    ln -s -f $(realpath $MASCOPE_PRIVATE_DATADIR) $MASCOPE_UI
    # (re)set up nginx configuration for the static mascope frontend
    sudo systemctl stop nginx
    sudo rm -r -f /var/www/mascope.site || true
    sudo mkdir /var/www/mascope.site
    sudo ln -s -f $MASCOPE_UI /var/www/mascope.site/production
    sed "s/MASCOPE_PUBLIC_HOST/$MASCOPE_PUBLIC_HOST/g;s/MASCOPE_PUBLIC_PORT/$MASCOPE_PUBLIC_PORT/g;s/MASCOPE_PUBLIC_API_PORT/$MASCOPE_PUBLIC_API_PORT/g;" $MY_PATH/nginx/mascope_site.conf > $MY_PATH/nginx/mascope.com
    sudo mv -f $MY_PATH/nginx/mascope.com /etc/nginx/sites-available/mascope.com
    sudo chmod -x /etc/nginx/sites-available/mascope.com
    # create and deploy self-signed ssl certificate for https access to nginx
    sudo openssl req -config $MY_PATH/nginx/ssl.params -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/ssl/private/nginx.key -out /etc/ssl/certs/nginx.crt
    sudo cp -f $MY_PATH/nginx/self-signed.conf /etc/nginx/snippets/self-signed.conf
    sudo chmod 644 /etc/nginx/snippets/self-signed.conf
    # enable mascope site
    sudo ln -s -f /etc/nginx/sites-available/mascope.com /etc/nginx/sites-enabled/mascope.com
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo gpasswd -a www-data $USER
    sudo systemctl restart nginx
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
MASCOPE_UI=$HOME/mascope_ui
# MASCOPE_UI=$(realpath $(dirname $MY_PATH))
# MASCOPE_PROJECT=$(realpath $MY_PATH/../..)

install_candies
install_prerequisites
install_default_dev_env

echo 
echo AAA MASCOPE frontend setup finished. 
echo 

exit 0
