<template>
  <div id="services">
    <div class="field">
      <b-radio
          v-model="datatab_service_model"
          name="ui_service"
          :type="datatab_service_status_color"
          :title="datatab_service_title"
          native-value="ui">
          <span class="services-title">UI service: </span> 
          <span class="services-status">{{ datatab_service_title }}</span>
      </b-radio>
    </div>
    <div class="field services-status">
        <section>
            <b-radio
                v-model="scenthound_service_model"
                :type="scenthound_service_status_color"
                :title="scenthound_service_title"
                name="scenthound"
                native-value="scenthound">
                <span class="services-title">Scenthound service: </span>  
                <span class="services-status">{{ scenthound_service_title }}</span>  
            </b-radio>
            <b-button icon-left="restore" type="is-dark" size="is-small" @click="restart_service('scenthound_service.py')"></b-button>
            &nbsp; 
            <b-button icon-left="stop-circle-outline" type="is-dark" size="is-small" @click="stop_service('scenthound_service.py')"></b-button>
        </section>
    </div>
  </div>
</template>

<script type="text/javascript">
"use strict"; 

import Vue from "vue";
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';

var ps = require("python-shell"); 
const kill  = require('tree-kill');
const process = require('process');


Vue.use(Buefy); 
var spawned_childs = []; 
const compiler_path = "__dirname/../py/App/Python/python.exe";
const script_path = "__dirname/../py_code/";
var services = [
            // "DataTabService.py", 
            // "MeasurementTabService.py",
        ];
var remote = require('electron').remote; 

var dot_env_vars = remote.getGlobal('dot_env_vars'); 
// var datatab_server_url = dot_env_vars.protocol+"://"+ dot_env_vars.host+":"+ dot_env_vars.datatab_service_port+"/";
var scenthound_server_url = dot_env_vars.protocol+"://"+ dot_env_vars.host+":"+ dot_env_vars.scenthound_service_port+"/";

var pyshell_options = {
    mode: 'text',
    pythonPath: compiler_path, 
    pythonOptions: ['-u'], // get print results in real-time
    scriptPath: script_path,
    args: []
};


import io from 'socket.io-client';
// var datatab_service_socket = io.connect(datatab_server_url, {timeout: 60000, autoConnect: true, reconnectionDelay: 500, reconnection: true}); 
var scenthound_service_socket = io.connect(scenthound_server_url); 

export default {
    name: "ServiceStatus",
    data:function(){
        return{
            datatab_service_model: "ui", 
            datatab_service_is_alive: false, 
            datatab_service_title: "Offline", 
            datatab_service_status_color: "is-danger", 
            scenthound_service_model: "scenthound",
            scenthound_service_is_alive:false, 
            scenthound_service_title: "Offline", 
            scenthound_service_status_color: "is-danger",   
            loaded_services_pid_map: {}, 
        }
    }, 
    created() {
        // datatab_service_socket.on("connect", ()=>{
        //     console.log("Connected to datatab service in Service status tab. "); 
        // }); 
        // datatab_service_socket.on("disconnect", ()=>{
        //     console.log("Disconnected to datatab service in Service status tab. ");
        // });
        scenthound_service_socket.on("connect", ()=>{
            console.log("Connected to scenthound service in Service status tab. ");
        }); 
        scenthound_service_socket.on("disconnect", ()=>{
            console.log("Disconnected to scenthound service in Service status tab. ")
        });   
        scenthound_service_socket.on("update_scenthound_health_status_in_tray", (json_data)=>{
            // console.log(json_data); 
            var service_name = json_data.service_name; 
            var service_status = json_data.service_status; 

            if (service_name === "scenthound" && service_status === "running"){
                this.scenthound_service_is_alive = true; 
            }else{
                this.scenthound_service_is_alive = false; 
            }     
        });
        // datatab_service_socket.on("update_ui_health_status_in_tray", (json_data)=>{
        //     var service_name = json_data.service_name; 
        //     var service_status = json_data.service_status; 
        //     if (service_name === "ui" && service_status === "running"){
        //         this.datatab_service_is_alive = true; 
        //     }else{
        //         this.datatab_service_is_alive = false; 
        //     }        
        // });
    },
    mounted: function() {
        this.start_services(); 
        this.reset_services_status(); 
        window.addEventListener("beforeunload", this.close_services);
    }, 
    methods:{
        start_service(pyfile, failed_count=1){
            var self = this; 
            var child_processes = null; 

            child_processes=ps.PythonShell.run(pyfile, pyshell_options, function (err, results) {
                if (err) {
                    console.log("Error happened! Failed to run "+pyfile+" ...");
                    console.log(err); 
                    if(failed_count<=10){
                        self.start_service(pyfile, failed_count++); 
                    }
                    //throw err;
                }
                console.log(results);
            });                    
            self.loaded_services_pid_map[pyfile] = child_processes.childProcess.pid; 
        },
        stop_service:function(pyfile){
            var pid = this.loaded_services_pid_map[pyfile];
            if(pid){
                process.kill(pid);    
            }
        },
        restart_service: function(pyfile){
            var self = this; 
            try{
                self.stop_service(pyfile); 
            }catch(err){
                console.log(err); 
            }
            self.start_service(pyfile); 
        },
        start_services: function() {
            // start the UI Service
            for(var i = 0; i < services.length; i++){
                // console.log(services[i]+" - started"); 
                // spawned_childs[i] = spawn(compiler_path,["__dirname/../py_code/"+ services[i]]);  
                this.start_service(services[i]); 
            }
        },
        reset_services_status: function(){
            var self = this; 
            setInterval(function(){
                self.datatab_service_is_alive = false; 
                self.scenthound_service_is_alive = false; 
            }, 10000); 
        },
        close_services: function(){
            for(var i=0; i<spawned_childs.length; i++){
                kill(spawned_childs[i].pid); 
            }
        }
    },
    watch:{
        datatab_service_is_alive: function(new_val, old_val){
            if(new_val === old_val){
                return false; 
            }
            if(new_val === true){
                this.datatab_service_status_color = "is-success"; 
                this.datatab_service_title = "Online"; 
            }else{
                this.datatab_service_status_color = "is-danger"; 
                this.datatab_service_title = "Offline";
            }
        },
        scenthound_service_is_alive: function(new_val, old_val){
            if(new_val === old_val){
                return false; 
            }
            if(new_val === true){
                this.scenthound_service_status_color = "is-success"; 
                this.scenthound_service_title = "Online"; 
            }else{
                this.scenthound_service_status_color = "is-danger"; 
                this.scenthound_service_title = "Offline";
            }
        }, 
    }

}
</script>

<style scoped>
  #app{
    text-align: center; 
  }
  .services-title{
    font-family: Cambria, Cochin, Georgia, Times, 'Times New Roman', serif;
    font-size:1.2rem;
    font-weight: 700; 
  }
  .services-status{
    font-family: Cambria, Cochin, Georgia, Times, 'Times New Roman', serif;
    font-size: 1rem;
    font-weight: 400; 
  }
  #services{
    height: 100vh;
    /* width: 492px; 
    height: 220px; */
    padding:20px; 
    border: 1px solid #fff;
  }
</style>
