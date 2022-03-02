import { createConnectedStore } from '$lib/api';

import modal from './modules/modal';
import key from './modules/key';
import workspace from "./modules/workspace";
import target from "./modules/target";
import sample from "./modules/sample";
import match from "./modules/match";

export default createConnectedStore({
	state: {
		query: null
	},
	modules: {
		modal,
		key,
		workspace,
		sample,
		target,
		match,
	},
});
