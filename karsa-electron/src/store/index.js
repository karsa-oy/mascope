import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
	state: {
		acquisition_status: "not_running",		// not_running/starting/running/stopping
		autosave_on: false,
		compute_target_ions: {},
		data_source_selected: {},
		experiment_selected: { 'title': "", 'project': "", 'attributes': [] },
		experiments: [],
		figure_data: {},
		figure_double_click: null,
		figure_ranges: {},
		identified_ions: {},
		identify_peaks: {},
		ionization_mechanism: "",
		mz_calibration: {},
		new_file: "",
		peak_data: {},
		project_selected: { 'title': "", 'attributes': [] },
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
		target_ions: [],
		target_to_display: null,
		tofdaq_log_entry: {},
		url: "",
		visualize_range: {},
	},
	mutations: {
		acquisition_status(state, payload) {
			state.acquisition_status = payload;
		},
		autosave_on(state, payload) {
			state.autosave_on = payload;
		},
		compute_target_ions(state, payload) {
			state.compute_target_ions = payload;
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
		identified_ions(state, payload) {
			state.identified_ions = payload;
		},
		identify_peaks(state, payload) {
			state.identify_peaks = payload;
		},
		integrate_target_ions(state, payload) {
			state.integrate_target_ions = payload;
		},
		ionization_mechanism(state, payload) {
			state.ionization_mechanism = payload;
		},
		mz_calibration(state, payload) {
			state.mz_calibration = payload;
		},
		new_file(state, payload) {
			state.new_file = payload;
		},
		peak_data(state, payload) {
			state.peak_data = payload;
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
		target_ions(state, payload) {
			state.target_ions = payload;
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
