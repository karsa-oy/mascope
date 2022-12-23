### Deploy staging version of Mascope application (backend + frontend)

#### Get build environment ready:
 Make sure Vagrantfile and corresponding .env contain required values

#### Deploy Mascope app (linux VirtualBox on Windows host):

First build new mascope UI distribution package by running build_dist.cmd.
Then mascope services are started in a linux VirtualBox: vagrant up.
All this can be done on Windows host by running corresponding deploy.cmd:

 - Ubuntu 2004 with python 3.8:
    deploy_py38.cmd

 - Ubuntu 2204 with python 3.10:
    deploy_py310.cmd

#### Or on native linux environment:

1. Check out mascope sources and have mascope UI package ready (built from frontend project)
2. Roll out mascope services on native Ubuntu

    provision_box.sh

