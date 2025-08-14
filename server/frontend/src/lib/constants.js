export const alarmsList = ['TARGETS']

export const collectionTypes = ['TARGETS', 'DIAGNOSTICS', 'CALIBRANTS']

export const batchTypes = ['ACQUISITION', 'ANALYSIS']
export const DEFAULT_SAMPLE_BATCH_TYPE = 'ANALYSIS' // TODO should read from api configs DEFAULT_SAMPLE_BATCH_TYPE?
export const ACQUISITION_POLARITY = ['+', '-']
export const ANALYSIS_POLARITY = '+-'

// Collection type constraints for sample batch types
export const collectionBatchTypes = {
  TARGETS: ['ANALYSIS'],
  DIAGNOSTICS: ['ACQUISITION', 'ANALYSIS'],
  CALIBRANTS: ['ANALYSIS']
}

export const batchCollectionTypes = {
  ANALYSIS: ['TARGETS', 'DIAGNOSTICS', 'CALIBRANTS'],
  ACQUISITION: ['DIAGNOSTICS']
}

export const getAllowedWorkspaceTypes = (collectionType) => {
  return collectionBatchTypes[collectionType] || []
}

export const getAllowedBatchTypes = (collectionType) => {
  return collectionBatchTypes[collectionType] || []
}

export const getAllowedCollectionTypes = (batchType) => {
  return batchCollectionTypes[batchType] || []
}

// Sample types by filter ID requirement
export const sampleTypesFilterIdRequired = ['FILTER_REGENERATION', 'FILTER_BACKGROUND']
export const sampleTypesFilterIdOptional = ['BLANK', 'SAMPLE', 'UNKNOWN']
export const sampleTypesFilterIdNotAllowed = ['INSTRUMENT_BACKGROUND', 'ONLINE']

// Combined sample types for validation
export const sampleTypes = [
  ...sampleTypesFilterIdRequired,
  ...sampleTypesFilterIdOptional,
  ...sampleTypesFilterIdNotAllowed
]
