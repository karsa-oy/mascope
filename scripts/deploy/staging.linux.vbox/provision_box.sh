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


function source_project_env() {
    # use production .env
    # .env should be in project root, when restarting mascope be service
    # if .debug_env is present, concatenate
    cp -f $MY_PATH/.env $MASCOPE_PROJECT/.env
    if [ -f $MY_PATH/.debug_env ]; then
        echo AAA Overlay $MY_PATH/.debug_env
        echo >> $MASCOPE_PROJECT/.env
        cat $MY_PATH/.debug_env >> $MASCOPE_PROJECT/.env
    fi
    source $MASCOPE_PROJECT/.env
}


function set_up_mascope_frontend() {
    # frontend web server
    rm -r -f $MASCOPE_UI || true
    cp -r -f $MASCOPE_PROJECT/frontend/dist $MASCOPE_UI
    # create mascope db link (MASCOPE_PRIVATE_DATADIR may be relative to backend)
    pushd $MASCOPE_PROJECT/backend
    ln -s -f $(realpath $MASCOPE_PRIVATE_DATADIR) $MASCOPE_UI
    popd 
    # (re)set up nginx configuration for the static mascope frontend
    sudo systemctl stop nginx
    sudo rm -r -f /var/www/mascope.site || true
    sudo mkdir /var/www/mascope.site
    sudo ln -s -f $MASCOPE_UI /var/www/mascope.site/production
    sed "s/MASCOPE_PUBLIC_PORT/$MASCOPE_PUBLIC_PORT/g;s/MASCOPE_PUBLIC_API_PORT/$MASCOPE_PUBLIC_API_PORT/g;" $MY_PATH/nginx/mascope_site.conf > $MY_PATH/nginx/mascope.com
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


function stop_mascope_backend() {
    # kill mascope backend services and corresponding log-rotates from prev.session if any
    pkill -f file-converter || true
    pkill -f file-downloader || true
    pkill -f mascope-api || true
    pkill log-rotate || true
    # release mascope-api port if any
    sudo lsof -t -i:$MASCOPE_PUBLIC_API_PORT && sudo kill -9 $(sudo lsof -t -i:$MASCOPE_PUBLIC_API_PORT) || true
}


function start_mascope_backend() {
    pushd $MASCOPE_PROJECT/backend

    echo AAA start mascope-api process...
    PYTHONUNBUFFERED=1 poetry run mascope-api |& poetry run log-rotate -n=7000 -l=$MASCOPE_PRIVATE_LOG_DIR/mascope_api.log &

    # echo AAA start file convertor for KLTOF1...
    # PYTHONUNBUFFERED=1 poetry run file-converter --config ./backend/service/file_converter_config/KLTOF1.yaml --ping |& poetry run log-rotate -n=5000 -l=$MASCOPE_PRIVATE_LOG_DIR/converter_KLTOF1.log &

    # echo AAA start file convertor for KLTOF2...
    # PYTHONUNBUFFERED=1 poetry run file-converter --config ./backend/service/file_converter_config/KLTOF2.yaml --ping |& poetry run log-rotate -n=5000 -l=$MASCOPE_PRIVATE_LOG_DIR/converter_KLTOF2.log &

    # echo AAA start file convertor for KORBI1...
    # PYTHONUNBUFFERED=1 poetry run file-converter --config ./backend/service/file_converter_config/KORBI1.yaml --ping |& poetry run log-rotate -n=5000 -l=$MASCOPE_PRIVATE_LOG_DIR/converter_KORBI1.log &

    # echo AAA start file downloader for KLTOF1...
    # PYTHONUNBUFFERED=1 poetry run file-downloader --config ./backend/service/file_downloader_config/KLTOF1.yaml --ping |& poetry run log-rotate -n=1000 -l=$MASCOPE_PRIVATE_LOG_DIR/downloader_KLTOF1.log &

    # echo AAA start file downloader for KLTOF2...
    # PYTHONUNBUFFERED=1 poetry run file-downloader --config ./backend/service/file_downloader_config/KLTOF2.yaml --ping |& poetry run log-rotate -n=1000 -l=$MASCOPE_PRIVATE_LOG_DIR/downloader_KLTOF2.log &

    # echo AAA start file downloader for KORBI1...
    # PYTHONUNBUFFERED=1 poetry run file-downloader --config ./backend/service/file_downloader_config/KORBI1.yaml --ping |& poetry run log-rotate -n=1000 -l=$MASCOPE_PRIVATE_LOG_DIR/downloader_KORBI1.log &

    popd
}


function install_prerequisites() {
    echo AAA Install needed packages
    sudo apt-get update
    # sudo apt-get install -y firefox
    sudo apt-get install -y patchelf
    sudo apt-get install -y nginx
    sudo apt-get install -y mono-complete
    sudo apt-get install -y python3-pip

    echo AAA setting up mascope backend environment...

    source_project_env

    # backend
    pushd $MASCOPE_PROJECT/backend
    pip install --user poetry
    echo $PATH | grep ~/.local/bin: || echo "export PATH=\"$HOME/.local/bin:$PATH\"" >> ~/.bashrc
    echo $PATH | grep ~/.local/bin: || export PATH="$HOME/.local/bin:$PATH"
    poetry update
    poetry lock --no-update
    poetry install --no-interaction --no-root
    # patch libtwh5.so RPATH for libtwtool.so dependency
    TWLIBPATH=$(realpath ./hardware/tofwerk/lib/dlls/linux_x86_64)
    patchelf --force-rpath --set-rpath "$TWLIBPATH" "$TWLIBPATH/libtwh5.so"
    popd

    echo AAA setting up mascope frontend...
    set_up_mascope_frontend

    echo AAA setting up mascope backend service...
    stop_mascope_backend
    start_mascope_backend
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
MASCOPE_PROJECT=$(realpath $MY_PATH/../../..)
MASCOPE_UI="$HOME/mascope_ui"

install_candies
install_prerequisites
install_default_dev_env

echo 
echo AAA setup finished. 
echo 

exit 0
