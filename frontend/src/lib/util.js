export function camelToSnakeCase(str) {
    return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
}

export function parseAutosamplerCsv(rows) {
    function explodeSequenceStep(step) {
        let result = [];
        const cycles = step['Cycle(s)'];
        delete step['Cycle(s)'];
        for (let i=0; i<cycles; ++i) {
            result.push(step)
        }
        return result
    }
    let result = [];
    var sequenceStep = {};
    for (let row of rows) {
        for (let cellKey in row) {
            const [key, value] = row[cellKey].split(':');
            if (key == "Sequence step"
                || Object.keys(sequenceStep).includes('Sequence step')
                ) {
                // New sequence step or append existing step
                if (key && key.length) {
                    sequenceStep[key.trim()] = value.trim();
                }
            }
        }
        if (Object.keys(sequenceStep).includes('Presence')) {
            // Sequence step complete
            result.push(...explodeSequenceStep(sequenceStep));
            sequenceStep = {};
        } 
    }
    return result
}