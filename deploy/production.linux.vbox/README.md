### Deploy production version of Mascope application (backend + frontend)

#### Build new distribution package for mascope UI

Normally you do it in your dev.environment (here: Windows). This will build frontend/dist folder with a code for static web server:
    build_dist.cmd

#### Deploy Mascope app:

For setting up Mascope application from Windows:
    vagrant up
- will set it up in Ubuntu VirtualBox;

or in native Ubuntu linux environment
    provision_box.sh

