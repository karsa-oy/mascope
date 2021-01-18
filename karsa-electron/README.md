### Description 
This project contains karsa-electron - Karsa desktop client application.

Front-end/back-end prototypes can be found here:
1. Karsa Desktop client application - https://bitbucket.org/kausiala/karsa-electron/
2. Karsa Router and backend services - https://gitlab.com/karsa_dev/karsa-backend


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
yarn electron:build

### Compile, build and publish distribution package (to github.com)
yarn electron:publish

### Customize configuration
See [Configuration Reference](https://cli.vuejs.org/config/).
