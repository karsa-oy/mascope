export default {
    namespaced: true,
    state: {
        // match params
        probableMatchThreshold: 0.9,
        possibleMatchThreshold: 0.5,
        mzTolerance: 100, // ppm
        isoRatioTolerance: 10, // %
        // peak params
        peakMinIntensity: 1,
        peakMinSeparation: 3,
        mzRange: null,
        tRange: null,
    },
}