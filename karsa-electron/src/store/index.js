import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
	state: {
		active_tab: 0,
		acquisition_started: {},
		acquisition_status: "not_running",		// not_running/starting/running/stopping
		acquisition_progress: {"sync": '', "progress": 0},
		h5_samples: [],
		h5_streamer_status: "not_ready",		// not_ready/ready
		h5_to_import: [],
		import_h5_table_datetime_range: {},
		import_sample_table_datetime_range: {},
		importable_samples: {},
		instrument_status: "not_ready",			// not_ready/ready
		sample_length: 120,
		sample_to_load: {},
		target_to_load: [],
		target_table_data: [],
		figure_ranges: {},
		visualize_range: {},
		tps_parameters: [],
		tps_parameters_selected: [],
		heatmap_figure_data: {},
		timeseries_figure_data: {},
		spec_stack_figure_data: {},
		sample_attributes: {},
		sample_selected: {},
		samples: [],
		project_selected: {'id': ""},
		projects: [],
		experiment_selected: {'id': ""},
		experiments: [],
		// sample_cache: {},
	},
	mutations: {
		active_tab(state, payload) {
			state.active_tab = payload;
		},
		acquisition_started(state, payload) {
			state.acquisition_started = payload;
		},
		acquisition_status(state, payload) {
			state.acquisition_status = payload;
		},
		acquisition_progress(state, payload) {
			state.acquisition_progress = payload;
		},
		samples(state, payload) {
			state.samples = payload;
		},
		h5_samples(state, payload) {
			state.h5_samples = payload;
		},
		h5_streamer_status(state, payload) {
			state.h5_streamer_status = payload;
		},
		h5_to_import(state, payload) {
			state.h5_to_import = payload;
		},
		import_h5_table_datetime_range(state, payload) {
			state.import_h5_table_datetime_range = payload;
		},
		import_sample_table_datetime_range(state, payload) {
			state.import_sample_table_datetime_range = payload;
		},
		importable_samples(state, payload) {
			state.importable_samples = payload;
		},
		instrument_status(state, payload) {
			state.instrument_status = payload;
		},
		sample_length(state, payload) {
			state.sample_length = payload;
		},
		sample_to_load(state, payload) {
			state.sample_to_load = payload;
		},
		target_to_load(state, payload) {
			state.target_to_load = payload;
		},
		target_table_data(state, payload) {
			state.target_table_data = payload;
		},
		figure_ranges(state, payload) {
			state.figure_ranges = payload;
		},
		visualize_range(state, payload) {
			state.visualize_range = payload;
		},
		tps_parameters(state, payload) {
			state.tps_parameters = payload;
		},
		tps_parameters_selected(state, payload) {
			state.tps_parameters_selected = payload;
		},
		heatmap_figure_data(state, payload) {
			state.heatmap_figure_data = payload;
		},
		timeseries_figure_data(state, payload) {
			state.timeseries_figure_data = payload;
		},
		spec_stack_figure_data(state, payload) {
			state.spec_stack_figure_data = payload;
		},
		sample_attributes(state, payload) {
			state.sample_attributes = payload;
		},
		project_selected(state, payload) {
			state.project_selected = payload;
		},
		projects(state, payload) {
			state.projects = payload;
		},
		experiment_selected(state, payload) {
			state.experiment_selected = payload;
		},
		experiments(state, payload) {
			state.experiments = payload;
		},
		// sample_cache(state, payload) {
		// 	state.sample_cache = payload;
		// },
	},
	actions: {
		//
	},
	getters: {
		//
	},
})
