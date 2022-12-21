#!/bin/bash
# ================================================================
# Set up dev environment on Ubuntu 1804
#
set -eu -o pipefail

#set -x
#trap read debug

os_name=$(lsb_release -si)
os_version=$(echo $(cat /etc/os-release | grep '^VERSION_ID=') | cut -d '"' -f 2)

if [[ $os_name != "Ubuntu" || $os_version < "18" ]]; then
	echo AAA $0 is supposed to run on Ubuntu 18 or newer, while current one is ${os_name} ${os_version}
	exit 1
fi

function register_on_reboot() {
  if [ ! -f /etc/rc.local ]; then
    echo "#!/bin/bash" | sudo tee /etc/rc.local
    sudo chmod +x /etc/rc.local
  fi
  cat /etc/rc.local | grep "$1" || echo "$1" | sudo tee -a /etc/rc.local
}

function install_prerequisites() {
  echo AAA Install MASCOPE bundle...

  pushd $MY_PATH
  source .env

  # make sure needed folders exist
  [ ! -d "$MASCOPE_PRIVATE_DATADIR" ] && mkdir -p $MASCOPE_PRIVATE_DATADIR
  [ ! -d "$MASCOPE_PRIVATE_CONVERTER_DIR" ] && mkdir -p $MASCOPE_PRIVATE_CONVERTER_DIR
  [ ! -d "$MASCOPE_PRIVATE_DOWNLOADER_DIR" ] && mkdir -p $MASCOPE_PRIVATE_DOWNLOADER_DIR
  [ ! -d "$MASCOPE_PRIVATE_LOG_DIR" ] && mkdir -p $MASCOPE_PRIVATE_LOG_DIR
  [ ! -d "$MASCOPE_PRIVATE_CONFIG_DIR" ] && mkdir -p $MASCOPE_PRIVATE_CONFIG_DIR
  
  # install backend
  tar -xvf mascope_backend.tar.gz
  chmod +x mascope_backend/setup.sh
  ./mascope_backend/setup.sh
  # install frontend
  tar -xvf mascope_ui.tar.gz
  chmod +x mascope_ui/setup.sh
  ./mascope_ui/setup.sh
  # drop mascope install helper to home bin dir
  cp -f mascope-install ~/.local/bin
  chmod +x ~/.local/bin/mascope-install
  # cleanup
  rm -rf mascope_backend
  rm -rf mascope_ui
  # update PATH for new backend services in this session
  echo $PATH | grep ~/.local/bin: || echo "export PATH=\"$HOME/.local/bin:$PATH\"" >> ~/.bashrc
  echo $PATH | grep ~/.local/bin: || export PATH="$HOME/.local/bin:$PATH"
  # make mascope backend persistent
  register_on_reboot "sudo -i -u $USER /home/$USER/.local/bin/mascope-run-backend"
  # run mascope backend in this session
  mascope-run-backend
  popd
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

install_candies
install_prerequisites
install_default_dev_env

echo 
echo AAA MASCOPE bundle setup finished. 
echo 

exit 0
