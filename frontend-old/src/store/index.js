import { createStore } from 'vuex'
import pathify from 'vuex-pathify'

import logger from './plugins/logger'
import api from './plugins/api'

import {
  app,
  batch,
  calibration,
  instrument,
  key,
  modal,
  notification,
  sample,
  targets,
  visualization,
  workspace,
} from './modules'

pathify.options.mapping = 'simple'

export default createStore({
  modules: {
    app,
    batch,
    calibration,
    instrument,
    key,
    modal,
    notification,
    sample,
    targets,
    visualization,
    workspace,
  },
  plugins: [
    // plugin order matters!
    logger, // logging first, so that next plugins log
    pathify.plugin, // pathify is a dependency of the api plugin
    api, // this last, so it has access to pathify
  ],
})
