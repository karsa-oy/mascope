export const num = {
  // 34.2146
  mz: new Intl.NumberFormat('en-US', {
    minimumIntegerDigits: 2,
    minimumFractionDigits: 4,
    maximumFractionDigits: 4
  }),
  mzError: new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }),
  isotopeSimilarity: new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }),
  peakIntensity: new Intl.NumberFormat('en-US', {
    notation: 'scientific',
    minimumSignificantDigits: 4,
    maximumSignificantDigits: 4
  }),
  relativeAbundance: new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3
  }),
  relativeAbundanceError: new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }),
  ticFraction: new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}
