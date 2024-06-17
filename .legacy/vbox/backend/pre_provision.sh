#!/bin/bash

## The script runs inside host box
## to ensure proper initialisations and 
## to fix possible Windows-related problems


echo AAA Prepare for dev provisioning...


my_folder=$(dirname $(realpath $BASH_SOURCE))
pushd $my_folder

sudo apt-get update -y
sudo apt-get install -y dos2unix

echo AAA workaround: fix possible broken line endings after editing scripts in Windows
find . -name "provision*.sh" | sudo xargs dos2unix

echo AAA workaround: set x bits for shell scripts
find . -name "provision*.sh" | sudo xargs chmod +x  

#echo AAA workaround: fix possible broken links in jenkins data, which may appear in Windows shared folders
#find /var/jenkins_home -xtype l | sudo xargs rm >/dev/null 2>&1

popd
exit 0
