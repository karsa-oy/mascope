### Description 
This folder contains the Mascope frontend.

Front-end/back-end sources can be found here:
1. Karsa Desktop client application - https://gitlab.com/karsa_dev/karsa_msview/frontend/
2. Karsa Router and backend services - https://gitlab.com/karsa_dev/karsa_msview/backend/

Front-end builds are found here:
https://github.com/karsa-dev/frontend/releases


### Setup Requirements 
* Node version 12.13.1
* yarn (package manager / recommended) or npm 

### Project setup
Call dev_setup.cmd to set up the project from the current repository.

### Compilation and hot-reloads for development
1) for Web version (web version will display error, as it's customized for electron)

yarn serve

2) for electron version (use this)

yarn electron:serve

### Compilation and minify for production
yarn build

### Lints and fixes files
yarn lint

### Compile and build distribution package
1) run checklist.cmd to make sure all build pre-requisits are in place

2) build the application

yarn electron:build

### Compile, build and publish distribution package (to github.com)
1) run checklist.cmd to make sure all build pre-requisits are in place

2) update package.json

3) build and publish the application

yarn electron:publish

### Customize configuration
See [Configuration Reference](https://cli.vuejs.org/config/).
