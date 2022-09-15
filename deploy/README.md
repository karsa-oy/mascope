### Deployment instructions

This module contains scripts for development and production deployments.
IMPORTANT: tmp solution: when deploying, store corresponding .env file to project root

### Development version for Windows

#### Manual deployment:
 1. cd dev.win
 2. deploy.cmd

#### Continuous deployment after each project update in git:
 1. cd dev.win
 2. deploy_loop.cmd
 
### Production version for Linux

#### Vagrant box:
 1. cd production.linux.vbox
 2. vagrant up

#### Native linux (Ubuntu):
 1. cd production.linux.vbox
 2. provision_box.sh
 
