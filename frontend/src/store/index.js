import { createConnectedStore } from '$lib/api';

import logger from "./plugins/logger";

import dev from "./modules/dev";
import modal from './modules/modal';
import key from './modules/key';
import workspace from "./modules/workspace";
import target from "./modules/target";
import sample from "./modules/sample";
import match from "./modules/match";
import template from "./modules/template";

export default createConnectedStore({
	state: {
		query: null
	},
	modules: {
		dev,
		modal,
		key,
		workspace,
		sample,
		target,
		match,
		template,
	},
	plugins: [
		logger
	]
});