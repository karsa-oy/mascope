### Description 
This project consists of two repositories

1. Karsa Desktop client application - https://bitbucket.org/kausiala/karsa-electron/src/master/  
2. Karsa data processors (python code) - https://bitbucket.org/kausiala/karsa2020/src/master/

The project is powered by self-consistent Portable Python 3.8.2 64-bit provided with the Karsa Desktop client.

Directory structure  
Karsa-Electron (Desktop client)  
    |---- py_code Directory (karsa2020 repository)
    |       |---- assets  
    |       |---- doc  
    |       |---- html  
    |       |---- karsaorbi  
    |       |---- karsatof  
    |       |---- UIClasses  
    |  
    |---- py Directory (Contains portable Python)   
    |---- Other Karsa Desktop js files  


### Setup Requirements 
* Node version 12.13.1  
* yarn (package manager / recommended) or npm   

### Project setup
1) Clone Karsa Desktop repo and cd path-to-project-repo-clone from commandline

2) then call install.bat in command line, this will clone other require repos and install the projects.  

### Compilation and hot-reloads for development
1) for Web version (web version will display error, as it's customized for electron)  

yarn serve  

2) for electron version (use this)  

yarn electron:serve  

### Compilation and minify for production
yarn build

### Lints and fixes files
yarn lint

### Compile for electron at the end 
yarn electron:build

### Customize configuration
See [Configuration Reference](https://cli.vuejs.org/config/).
