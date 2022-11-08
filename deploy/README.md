### Deployment instructions

This module contains scripts for development and production deployments.
When deploying, corresponding .env file will be copied to project root

### Development version for Windows

#### Get build environment ready:

 Make sure corresponding .env contains required values

#### Manual deployment:

 1. cd dev.win
 2. deploy.cmd

#### Continuous deployment after each project update in git:

 1. cd dev.win
 2. deploy_loop.cmd
 

### Production version for Linux

#### Vagrant box:

 1. cd production.linux.vbox
 2. deploy.cmd
 
#### Native linux (Ubuntu):

 1. Have mascope UI dist ready, or run on windows host :

    cd production.linux.vbox
    build_dist.cmd

 2. on linux guest:

    cd production.linux.vbox
    provision_box.sh

