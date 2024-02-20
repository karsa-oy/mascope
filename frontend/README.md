# Frontend

### Description

This folder contains the Mascope frontend, developed in [Vue.js](https://vuejs.org/). The dependencies are managed by [yarn](https://yarnpkg.com/).

```
mascope
├───agents
├───backend
├───frontend            # Mascope frontend
│   ├───scripts             # Build scripts
│   └───src                 # Frontend source code
│       ├───assets              # Icons, images, CSS
│       ├───components          # Vue components
│       ├───lib                 # Library (JS)
│       └───store               # Vuex store
└───scripts
```

### Setup Requirements

- [Node.js](https://nodejs.org/en)
- [yarn](https://yarnpkg.com/)

### Project setup

Call `yarn install` to install the dependencies.

### Compilation and hot-reloads for development

To run the frontend in development mode, call `yarn serve`.

### Lints and fixes files

`yarn lint`

### Compile and build distribution package

To build the frontend package, run `/scripts/build/build.cmd`. Refer to the README inside `/scripts/build` for more details.

### Customize configuration

See [Configuration Reference](https://cli.vuejs.org/config/).
