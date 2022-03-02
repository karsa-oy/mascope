'use strict';

import { app, protocol, BrowserWindow } from 'electron'
import { createProtocol } from 'vue-cli-plugin-electron-builder/lib';
import { autoUpdater } from "electron-updater";

const isDevelopment = process.env.NODE_ENV !== 'production';
const _ = require('underscore');

let parentWin;

const { ipcMain } = require('electron');
// Event handler for asynchronous incoming messages
ipcMain.on('asynchronous-message', (event, msg) => {
    if (msg === "closeSplashWin") {
        splashWin.close();
    }
});

// Scheme must be registered before the app is ready
protocol.registerSchemesAsPrivileged([{
    scheme: 'app',
    privileges: {
        secure: true,
        standard: true
    }
}]);

function launchMainApp() {
    parentWin.maximize();
    parentWin.show();
}

function createWindow() {
    // Create the browser window.
    parentWin = new BrowserWindow({
        width: 800,
        height: 600,
        show: false,
        webPreferences: {
            nodeIntegration: true,
        },
        frame: isDevelopment,
    });

    parentWin.on("closed", () => {
        parentWin = null;
        app.quit();
    });

    if (process.env.WEBPACK_DEV_SERVER_URL) {
        // Load the url of the dev server if in development mode
        parentWin.loadURL(process.env.WEBPACK_DEV_SERVER_URL)
        // service_statusWin.loadURL(process.env.WEBPACK_DEV_SERVER_URL+"service-status")
        if (!process.env.IS_TEST)
            parentWin.webContents.openDevTools();
    }
    else {
        createProtocol('app')
        // Load the index.html when not in development
        parentWin.loadURL('app://./index.html');
        autoUpdater.checkForUpdatesAndNotify();
    }
}

app.on("before-quit", (ev) => {
    ev.preventDefault();
    // some confirmation window also can go here before closing
});

// Quit when all windows are closed.
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.exit(0);
        // now close the app
        // On macOS it is common for applications and their menu bar
        // to stay active until the user quits explicitly with Cmd + Q
    }
})

app.on('activate', () => {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (parentWin === null) {
        createWindow();
    }
});

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', async () => {
    createWindow();
    launchMainApp();
    //launchSplashScreen();
});

// Exit cleanly on request from parent process in development mode.
if (isDevelopment) {
    if (process.platform === 'win32') {
        process.on('message', data => {
            if (data === 'graceful-exit') {
                app.quit();
            }
        })
    } else {
        process.on('SIGTERM', () => {
            app.quit()
        })
    }
}