'use strict'; 

import path from 'path';
import {app, protocol, BrowserWindow} from 'electron'
import { createProtocol,/**installVueDevtools */} from 'vue-cli-plugin-electron-builder/lib';
import { autoUpdater } from "electron-updater";

// const {Tray, Menu} = require("electron")
const isDevelopment = process.env.NODE_ENV !== 'production'; 
var dot_env_config = require('dotenv').config();
var _ = require('underscore');

var dotenv = {}; 
for (var key in dot_env_config.parsed ){
    var key_val = {}
    key_val[key] = dot_env_config.parsed[key]; 
    Object.assign(dotenv, key_val); 
}
// TODO: workaround, till url selection via UI is added
if ( !_.isEmpty(process.env.karsa_router_address) ) {
    const url = new URL(process.env.karsa_router_address);
    dotenv.protocol = url.protocol.replace(':', '');
    dotenv.host = url.hostname;
    dotenv.scenthound_service_port = url.port;
}
// make it global so other windows can use it
global.dot_env_vars = dotenv;

let parent_win;
let splash_win; 
// let service_status_win;
// let tray = null;

const {ipcMain} = require('electron'); 
// Event handler for asynchronous incoming messages
ipcMain.on('asynchronous-message', (event, msg) => {
    if(msg === "close_splash_win"){
        splash_win.close();
    }
 }); 
 
//  // Event handler for synchronous incoming messages
//  ipcMain.on('synchronous-message', (event, msg) => {
//     console.log(msg) 
//     event.returnValue = 'sync pong'
//  });


// Scheme must be registered before the app is ready
protocol.registerSchemesAsPrivileged([{
    scheme: 'app',
    privileges: {
        secure: true,
        standard: true
    }
}]); 


function launch_splash_screen(){
    createWindow();
    // createTray();

    splash_win = new BrowserWindow({
        width: 550,
        height: 350,
        transparent: true,
        resizable: false,
        frame: false,
        webPreferences: {
            nodeIntegration: true,
        }
    });
    splash_win.on("ready-to-show", function(event){
        event.preventDefault(); 
        splash_win.setMenu(null);
    }); 

    splash_win.on("close", function() {
        launch_main_app(); 
    });
 
    splash_win.on("closed", function() {
        splash_win = null;
    }); 

    if (process.env.WEBPACK_DEV_SERVER_URL)
    {
        // Load the url of the dev server if in development mode
        splash_win.loadURL(process.env.WEBPACK_DEV_SERVER_URL+"splash-window")  
        if (!process.env.IS_TEST) parent_win.webContents.openDevTools();
    } 
    else 
    {
        createProtocol('app')
        // Load the index.html when not in development
        splash_win.loadURL('app://./index.html#splash-window');
    }

//    splash_win.webContents.on("devtools-opened", () => { splash_win.webContents.closeDevTools(); });
}

function launch_main_app(){
    parent_win.maximize();
    // service_status_win.minimize();
    parent_win.show(); 
}

function createWindow() {
    // Create the browser window.
    parent_win = new BrowserWindow({
        width: 800,
        height: 600,
        show: false,
        webPreferences: {
            nodeIntegration: true,
        },
        // frame: false,
        // fullscreen: false,
    });

    // service_status_win = new BrowserWindow({
    //     width: 500,
    //     height: 220,
    //     resizable: false,
    //     parent: parent_win,
    //     webPreferences: {
    //         nodeIntegration: true,
    //         frame: false,
    //     }
    // });
    // service_status_win.on("minimize", function(event) {
    //     event.preventDefault();
    //     service_status_win.hide();
    // });
    // service_status_win.on("close", function(event) {
    //     event.preventDefault();
    //     service_status_win.hide();
    // });

    parent_win.on("closed", () => {
        parent_win = null;
        app.quit();   
    }); 

    if (process.env.WEBPACK_DEV_SERVER_URL)
    {
        // Load the url of the dev server if in development mode
        parent_win.loadURL(process.env.WEBPACK_DEV_SERVER_URL)
        // service_status_win.loadURL(process.env.WEBPACK_DEV_SERVER_URL+"service-status")
        if (!process.env.IS_TEST)
            parent_win.webContents.openDevTools();
    } 
    else 
    {
        createProtocol('app')
        // Load the index.html when not in development
        parent_win.loadURL('app://./index.html');
        // service_status_win.loadURL('app://./index.html#service-status');

        // const log = require("electron-log")
        // log.transports.file.level = "debug"
        // log.transports.file.fileName = 'karsa_log.log';
        // autoUpdater.logger = log
        autoUpdater.checkForUpdatesAndNotify();
    }

    // // hide the title bar
    // // parent_win.setMenu(null);
    // // service_status_win.setMenu(null);
    // // service_status_win.hide(); 
    // parent_win.hide();
}

// function show_window(window_name){
//     var window_ = eval(window_name);
//     window_.show();
// }
// function createTray() {
//     var trayIcnName = "test_ico.ico";
//     const trayIcnPath = process.env.WEBPACK_DEV_SERVER_URL ? path.join(__dirname, '../public/img/', trayIcnName) : path.join(__dirname, '../app.asar/img/', trayIcnName);
//     tray = new Tray(trayIcnPath)
//     const contextMenu = Menu.buildFromTemplate([
//         { label: 'Services Status', click(){show_window(service_status_win)}},

//     ])
//     tray.setToolTip('Karsa');
//     tray.setContextMenu(contextMenu);
//     // tray.on("click", function() {
//     //  service_status_win.show();
//     // });
// }

app.on("before-quit", (ev)=>{
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
    if (parent_win === null) {
        createWindow();
    }
});

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', async () => {
    if (isDevelopment && !process.env.IS_TEST) {
        // Install Vue Devtools
        // Devtools extensions are broken in Electron 6.0.0 and greater
        // See https://github.com/nklayman/vue-cli-plugin-electron-builder/issues/378 for more info
        // Electron will not launch with Devtools extensions installed on Windows 10 with dark mode
        // If you are not using Windows 10 dark mode, you may uncomment these lines
        // In addition, if the linked issue is closed, you can upgrade electron and uncomment these lines
        // try {
        //   await installVueDevtools()
        // } catch (e) {
        //   console.error('Vue Devtools failed to install:', e.toString())
        // }

    }
    launch_splash_screen();  
    // createWindow(); 
    // createTray(); 
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