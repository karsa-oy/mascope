import { createConnectedStore } from '$lib/api';

import workspace from "./modules/workspace";
import ui from './modules/ui';

export default createConnectedStore({
	state: {
		error: null,
		newFile: "",
		$datasetCoordUpdated: null,
	},
	modules: {
		workspace,
		ui,
	}
});
