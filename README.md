# Mascope

This is the primary developer documentation for Mascope.

- [Overview](#overview) - a birds-eye-view of the Mascope app
- [Getting started](#getting-started) - installing and running the dev environment
- [Frontend](#frontend) - the frontend
  - [Technologies](#frontend-technologies) - our frontend stack
  - [Folder structure](#frontend-folder-structure) - organization of the frontend code
  - [Tests](#frontend-tests) - our frontend tests

## Overview

This monorepo contains the Mascope backend and frontend as well auxiliary services, libraries and tooling. The project is structured as follows:

```
mascope/
  agents/          Instrument machine agents
    file_mover          File mover (for Orbitrap)
    ht300a              Autosampler
    tof_agent           Tofwerk TOF
  backend/         Main server (Python, FastAPI, SQLite)
  frontend/        Web client (Javascript, Vue, PrimeVue)
  libraries/       Shared libraries
    mascope_api/        Public REST API wrapper
    mascope_hardware/   Instrument interfaces
    mascope_lib/        Chemistry and signal processing
    mascope_runtime/    Config, logging and state
  notebooks/        Jupyter environment
  runtime/          Development runtime
  tooling/          CLI and scripts
```

Additionally, the `.legacy` folder persists some deprecated code and documentation, and the `.vscode` includes team VSCode configuration.

## Getting Started

Our development environment includes setup scripts and a comprehensive `mascope` command line tool. This section explains how to setup this environment.

### Windows

The only prerequisite is [Powershell 7](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows), which should be available on Windows 11 by default.

#### Installation

To install your development environment, run:

```
git clone git@github.com:karsa-oy/mascope.git && cd mascope && .\tooling\scripts\windows_dev_setup.ps1
```

The script will install our global dev tools _Python 3.12_, _Node 22_, _Pipx_ and _Poetry_, as well as dependencies for all our packages and the `mascope` cli.

After installation, run `mascope --help` for usage instructions.

#### Updating

When pulling the latest changes from github, we often need to ensure our development environment is updated.

To reinstall the `mascope` cli and development environment, run:

```
.\tooling\scripts\windows_dev_setup.ps1 -Update
```

This is much quicker than the full install, since it doesn't install the global dev tools.

# Frontend

Our frontend is a Single Page Application written in [Vue](https://vuejs.org/guide/introduction.html) and plain Javascript. It has been heavily refactored and redesigned in Q1/Q2 2024.

## Frontend technologies

The Mascope frontend is build with the following technologies:

- [Vue 3](https://vuejs.org/guide/introduction.html) frontend framework, using:
  - [Composition API](https://vuejs.org/guide/extras/composition-api-faq.html#what-is-composition-api)
  - [Single File Components](https://vuejs.org/api/sfc-spec.html)
  - [`<script setup>`](https://vuejs.org/api/sfc-script-setup.html#script-setup)
- [Pinia](https://pinia.vuejs.org/introduction.html) stores with the [setup store syntax](https://pinia.vuejs.org/core-concepts/#Setup-Stores)
- [PrimeVue](https://primevue.org/introduction/) as the component library
- [Vite](https://vitejs.dev/guide/) as the build tool + dev server
- [Playwright](https://playwright.dev/docs/intro) for end-to-end tests

## Frontend folder structure

The frontend folder structure is as follows:

```
public/       static files
scripts/      utility scripts
  build/        legacy build script
  palette.js    generates the Karsa palette
src/          source code
  api/          api client code
  lib/          shared library
  routes/        pages and navigation
  stores/        global app state
  ...         global vue app configs
tests/        playwright tests
  fixtures/     reusable test patterns
  ...
index.html    static template w/ font imports
package.json  npm package w/ dependencies
...           other tooling configs
```

The source code directory:

```
  api/         api client code
  lib/         shared library
    base/          shared components
    charts/        plotly charts (with own stores)
    dialogs/       interactive modals
    panes/         larger panels and tabs
    toolbars/      various menu bars
    config.js      mascope's config toml
    constants.js   alarms list, collection and sample types
    mzFit.js       calibration composable
    table.js       spreadsheet utilities
    utils.js       miscillanious utilities
  routes/       pages and navigation
    index.js       the router
    MainRoute      prod app (/)
    TestRoute      dev sandbox (/test)
  stores/       global app state
    data/         data stores w/ mutating APIs
      lib/
        module.js     standard data module constructor
      index.js      useData hook (see for more notes)
      ...           data modules
    ui/           ui stores w/ read-only APIs
      index.js      useUi hook
      ...           ui modules
    index.js      useApp hook
  App.vue       app root component, includes toaster
  main.js       vue app and primevue initialization
  palette.json  Karsa colors, generated by script
  style.css     global styles overriding the theme
  theme.js      Karsa theme = palette.js + PrimeVue Aura theme
```

## Frontend tests

Our frontend currently only has a handful of tests written in [Playwright](https://playwright.dev/docs/intro).
These are end-to-end tests which work by running headless browsers and emulating real user behavior like clicks.
The test then checks that certain elements are or are not visible in the page.

### Running the tests

To run the tests, you can run one of the following commands:

```
command               arg           usecase                description

npm run test          optional      test feature branch    run all tests on chrome only
npm run test:full     optional      test prod release      run all tests on chrome, safari & firefox
npm run test:only     required      debug failed tests     run one test
npm run test:trace    required      debug failed tests     run test with a trace
npm run test:headed   recommended   debug failed tests     run test(s) headed
npm run test:gen      none          write new tests        run the visual test generator
```

Here, the argument is a string with the name of the test or a keyword (playwright will
execute all tests matching the string). You can also run the tests directly with playwright,
refer to the Playwright docs for more details.

### Flakey tests

_⚠️ The tests tend to be quite flakey, and ofter rerunning them will make a failed test pass._

Use the debugging methods listed above when facing flakey tests. Often tests will be less flakey when
you run them in headed mode, and when you don't run them concurrently (this is why we configured Playwright
to use only one worker).
