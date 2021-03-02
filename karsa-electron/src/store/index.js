import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
	state: {
		active_tab: 1,
		acquisition_control_active: false,
		// acquisition_started: {},
		acquisition_status: "not_running",		// not_running/starting/running/stopping
		// acquisition_progress: {"sync": '', "progress": 0},
		experiment_selected: {'id': ""},
		experiments: [],
		// figure_ranges: {},
		// h5_samples: [],
		// h5_streamer_status: "not_ready",		// not_ready/ready
		// h5_to_import: [],
		// heatmap_figure_data: {},
		// import_h5_table_datetime_range: {},
		// import_sample_table_datetime_range: {},
		// importable_samples: {},
		// instrument_status: "not_ready",			// not_ready/ready
		project_selected: {'id': ""},
		projects: [],
		// sample_attributes: {},
		// sample_length: 120,
		sample_selected: {},
		sample_to_load: {},
		// samples: [],
		socket: null,
		// spec_stack_figure_data: {},
		// target_list_request: {},
		// target_table_data: [],
		target_to_display: {},
		// targets: [],
		// timeseries_figure_data: {},
		// tps_parameters: [],
		// tps_parameters_selected: [],
		url: "",
		// visualize_range: {},
		// stop_visualize_range: {},
	},
	mutations: {
		active_tab(state, payload) {
			state.active_tab = payload;
		},
		acquisition_control_active(state, payload) {
			state.acquisition_control_active = payload;
		},
		// acquisition_started(state, payload) {
		// 	state.acquisition_started = payload;
		// },
		acquisition_status(state, payload) {
			state.acquisition_status = payload;
		},
		// acquisition_progress(state, payload) {
		// 	state.acquisition_progress = payload;
		// },
		experiment_selected(state, payload) {
			state.experiment_selected = payload;
		},
		experiments(state, payload) {
			state.experiments = payload;
		},
		// figure_ranges(state, payload) {
		// 	state.figure_ranges = payload;
		// },
		// h5_samples(state, payload) {
		// 	state.h5_samples = payload;
		// },
		// h5_streamer_status(state, payload) {
		// 	state.h5_streamer_status = payload;
		// },
		// h5_to_import(state, payload) {
		// 	state.h5_to_import = payload;
		// },
		// heatmap_figure_data(state, payload) {
		// 	state.heatmap_figure_data = payload;
		// },
		// import_h5_table_datetime_range(state, payload) {
		// 	state.import_h5_table_datetime_range = payload;
		// },
		// import_sample_table_datetime_range(state, payload) {
		// 	state.import_sample_table_datetime_range = payload;
		// },
		// importable_samples(state, payload) {
		// 	state.importable_samples = payload;
		// },
		// instrument_status(state, payload) {
		// 	state.instrument_status = payload;
		// },
		room(state, payload) {
			state.room = payload;
		},
		// sample_attributes(state, payload) {
		// 	state.sample_attributes = payload;
		// },
		// sample_length(state, payload) {
		// 	state.sample_length = payload;
		// },
		sample_to_load(state, payload) {
			state.sample_to_load = payload;
		},
		// samples(state, payload) {
		// 	state.samples = payload;
		// },
		socket(state, payload) {
			state.socket = payload;
		},
		// spec_stack_figure_data(state, payload) {
		// 	state.spec_stack_figure_data = payload;
		// },
		// target_list_request(state, payload) {
		// 	state.target_list_request = payload;
		// },
		// target_table_data(state, payload) {
		// 	state.target_table_data = payload;
		// },
		target_to_display(state, payload) {
			state.target_to_display = payload;
		},
		// targets(state, payload) {
		// 	state.targets = payload;
		// },
		// timeseries_figure_data(state, payload) {
		// 	state.timeseries_figure_data = payload;
		// },
		// tps_parameters(state, payload) {
		// 	state.tps_parameters = payload;
		// },
		// tps_parameters_selected(state, payload) {
		// 	state.tps_parameters_selected = payload;
		// },
		url(state, payload) {
			state.url = payload;
		},
		// visualize_range(state, payload) {
		// 	state.visualize_range = payload;
		// },
		// stop_visualize_range(state, payload) {
		// 	state.s = payload;
		// },
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
