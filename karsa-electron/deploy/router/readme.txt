This is how to run Router in VirtualBox.

Pre-requisits:
- Oracle VirtualBox
- vagrant

Sequence:
- cd <project_root>/deploy/router
- vagrant up
- from the virtual terminal console: /vagrant/deploy/router/router_run.sh

How it works:
- first call of 'vagrant up' will create an Ubuntu vbox 'router-box';
- next calls of 'vagrant up' runs will just start it;
- log in to the vbox as vagrant:vagrant;
- start Router server from the vbox: '/vagrant/deploy/router/router_run.sh';
- ouside of the vbox, start other services as normal (<project_root>/run_scenthound.bat);
- if the vbox with Router is not running, then local Router server will be started as normal.
