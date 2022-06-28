import { createConnectedStore } from '$lib/api';

import logger from "./plugins/logger";

import calibration from "./modules/calibration";
import config from "./modules/config";
import dev from "./modules/dev";
import key from './modules/key';
import match from "./modules/match";
import modal from './modules/modal';
import sample from "./modules/sample";
import target from "./modules/target";
import template from "./modules/template";
import visualization from "./modules/visualization";
import workspace from "./modules/workspace";

export default createConnectedStore({
	state: {
		query: null
	},
	modules: {
		calibration,
		config,
		dev,
		key,
		match,
		modal,
		sample,
		target,
		template,
		visualization,
		workspace,
	},
	plugins: [
		logger
	]
});