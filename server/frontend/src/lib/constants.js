export const alarmsList = ['TARGETS']

export const collectionTypes = ['TARGETS', 'DIAGNOSTICS', 'CALIBRANTS']

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
