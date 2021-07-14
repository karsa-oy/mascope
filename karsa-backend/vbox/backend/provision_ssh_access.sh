#!/bin/bash -eu

## Normally vagrant removes external ssh access to the box:
## allow password authentication for ssh clients
## IMPORTANT: if you don't want ssh access from external client, comment out 
## the lower lines, otherwise, change predefined vagrant password!
echo AAA Allow external ssh access to the host box
sudo sed -i -e "s/ChallengeResponseAuthentication no/ChallengeResponseAuthentication yes/" /etc/ssh/sshd_config
sudo sed -i -e "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config
sudo systemctl restart sshd



