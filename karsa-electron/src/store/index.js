import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
	state: {
		acquisition_control_active: false,
		acquisition_status: "not_running",		// not_running/starting/running/stopping
		autosave_on: false,
		data_source_selected: {},
		experiment_selected: {'title': "", 'project': "", 'attributes': []},
		experiments: [],
		figure_data: {},
		figure_double_click: null,
		figure_ranges: {},
		new_file: "",
		project_selected: {'title': "", 'attributes': []},
		projects: [],
		root_namespace: null,
		sample_annotations: [],
		sample_annotation_timestamp: null,
		sample_selected: {
				'filename': "",
				'title': "",
				'attributes': [],
				'properties': {},
				'project': "",
				'experiment': "",
				},
		stop_visualize_range: {},
		target_to_display: {},
		tofdaq_log_entry: {},
		url: "",
		visualize_range: {},
	},
	mutations: {
		acquisition_control_active(state, payload) {
			state.acquisition_control_active = payload;
		},
		acquisition_status(state, payload) {
			state.acquisition_status = payload;
		},
		autosave_on(state, payload) {
			state.autosave_on = payload;
		},
		data_source_selected(state, payload) {
			state.data_source_selected = payload;
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
		project_selected(state, payload) {
			state.project_selected = payload;
		},
		projects(state, payload) {
			state.projects = payload;
		},
		root_namespace(state, payload) {
			state.root_namespace = payload;
		},
		sample_annotations(state, payload) {
			state.sample_annotations = payload;
		},
		sample_annotation_timestamp(state, payload) {
			state.sample_annotation_timestamp = payload;
		},
		sample_selected(state, payload) {
			state.sample_selected = payload;
		},
		stop_visualize_range(state, payload) {
			state.stop_visualize_range = payload;
		},
		target_to_display(state, payload) {
			state.target_to_display = payload;
		},
		tofdaq_log_entry(state, payload) {
			state.tofdaq_log_entry = payload;
		},		
		url(state, payload) {
			state.url = payload;
		},
		visualize_range(state, payload) {
			state.visualize_range = payload;
		},
	},
	actions: {
		//
	},
	getters: {
		//
	},
})
