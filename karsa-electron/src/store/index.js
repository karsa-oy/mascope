import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
	state: {
		acquisition_control_active: false,
		acquisition_status: "not_running",		// not_running/starting/running/stopping
		experiment_selected: {'id': ""},
		experiments: [],
		figure_data: {},
		figure_double_click: null,
		figure_ranges: {},
		new_file: "",
		project_selected: {'id': ""},
		projects: [],
		sample_selected: {},
		sample_to_load: {},
		root_namespace: null,
		target_to_display: {},
		url: "",
		data_source_selected: {},
	},
	mutations: {
		acquisition_control_active(state, payload) {
			state.acquisition_control_active = payload;
		},
		acquisition_status(state, payload) {
			state.acquisition_status = payload;
		},
		experiment_selected(state, payload) {
			state.experiment_selected = payload;
		},
		experiments(state, payload) {
			state.experiments = payload;
		},
		figure_double_click(state, payload) {
			state.figure_double_click = payload;
		},
		figure_data(state, payload) {
			state.figure_data = payload;
		},
		figure_ranges(state, payload) {
			state.figure_ranges = payload;
		},
		new_file(state, payload) {
			state.new_file = payload;
		},
		sample_to_load(state, payload) {
			state.sample_to_load = payload;
		},
		root_namespace(state, payload) {
			state.root_namespace = payload;
		},
		target_to_display(state, payload) {
			state.target_to_display = payload;
		},
		url(state, payload) {
			state.url = payload;
		},
		data_source_selected(state, payload) {
			state.data_source_selected = payload;
		},
		project_selected(state, payload) {
			state.project_selected = payload;
		},
		projects(state, payload) {
			state.projects = payload;
		},
	},
	actions: {
		//
	},
	getters: {
		//
	},
})
