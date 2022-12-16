### Build production version of mascope backend (mascope api server, file serivces...)


#### Get build environment ready:

 - .env contains backend parameters

#### Build mascope frontend:

 - build is done on Windows host with dev.environment installed;
 - run build.cmd; resulting tar archive contains the package;


#### Deploy mascope frontend:

 - untar the tar archive and run setup.sh
 - run mascope-run-backend to start backend services
 - check runtime logs in $MASCOPE_PRIVATE_LOG_DIR

