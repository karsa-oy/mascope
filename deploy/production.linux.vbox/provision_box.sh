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
    # sudo apt-get install -y firefox
    sudo apt-get install -y patchelf
    sudo apt-get install -y nginx
    sudo apt-get install -y mono-complete
    sudo apt-get install -y python3-pip

    echo AAA setting up mascope backend

    # use corresponding .env
    cp -f $MY_PATH/.env $MASCOPE_PROJECT/.env
    source $MASCOPE_PROJECT/.env

    # backend
    pushd $MASCOPE_PROJECT/backend
    pip install --user poetry
    echo $PATH | grep ~/.local/bin: || echo "export PATH=\"$HOME/.local/bin:$PATH\"" >> ~/.bashrc
    echo $PATH | grep ~/.local/bin: || export PATH="$HOME/.local/bin:$PATH"
    poetry update
    poetry lock --no-update
    poetry install --no-interaction --no-root
    # patch libtwh5.so RPATH for libtwtool.so dependency
    TWLIBPATH=$(realpath ./backend/lib/hardware/tofwerk/lib/dlls/linux_x86_64)
    patchelf --force-rpath --set-rpath "$TWLIBPATH" "$TWLIBPATH/libtwh5.so"
    popd

    echo AAA setting up mascope frontend...

    # frontend web server
    rm -r -f $MASCOPE_UI || true
    cp -r -f $MASCOPE_PROJECT/frontend/dist $MASCOPE_UI
    # create mascope db link (MASCOPE_PRIVATE_DATADIR may be relative to backend)
    pushd $MASCOPE_PROJECT/backend
    ln -s -f $(realpath $MASCOPE_PRIVATE_DATADIR) $MASCOPE_UI
    popd 
    # add sql.js library
    mkdir $MASCOPE_UI/node_modules
    cp -r -f $MASCOPE_PROJECT/frontend/node_modules/sql.js $MASCOPE_UI/node_modules
    # (re)set up nginx configuration for the static mascope frontend
    sudo systemctl stop nginx
    sudo rm -r -f /var/www/mascope.site || true
    sudo mkdir /var/www/mascope.site
    sudo ln -s -f $MASCOPE_UI /var/www/mascope.site/production
    sudo cp -f $MY_PATH/nginx/mascope_site.conf /etc/nginx/sites-available/mascope_site.conf
    sudo chmod -x /etc/nginx/sites-available/mascope_site.conf
    # create and deploy self-signed ssl certificate for https access to nginx
    sudo openssl req -config $MY_PATH/nginx/ssl.params -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/ssl/private/nginx.key -out /etc/ssl/certs/nginx.crt
    sudo cp -f $MY_PATH/nginx/self-signed.conf /etc/nginx/snippets/self-signed.conf
    sudo chmod 644 /etc/nginx/snippets/self-signed.conf
    # enable mascope site
    sudo ln -s -f /etc/nginx/sites-available/mascope_site.conf /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo systemctl restart nginx

    echo AAA setting up mascope backend service...

    sudo cp -f $MY_PATH/mascope.service /etc/systemd/system/
    sudo chmod -x  /etc/systemd/system/mascope.service
    sudo systemctl daemon-reload
    sudo systemctl enable mascope
    sudo systemctl start mascope
}


function install_candies() {
    echo AAA Set Helsinki time zone
    sudo timedatectl set-timezone Europe/Helsinki
#    echo "Europe/Helsinki" | sudo tee /etc/timezone
#    sudo dpkg-reconfigure --frontend noninteractive tzdata

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
MASCOPE_PROJECT=$(realpath $MY_PATH/../..)
MASCOPE_UI="$HOME/mascope_ui"

install_candies
install_prerequisites
install_default_dev_env

echo 
echo AAA setup finished. 
echo 

exit 0
