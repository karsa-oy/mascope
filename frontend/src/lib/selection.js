export default {
    propegateDown(row) {
        // calculate selection for level and child levels
        let currentSelection = row._selected;
        let nextSelection;
        switch (currentSelection) {
            case 'all':
                nextSelection = 'none';
                break;
            case 'some':
                nextSelection = 'all';
                break;
            case 'none':
                nextSelection = 'all';
                break;
        }
        return nextSelection;
    },
    propegateUp(childRows) {
        let all = childRows.every((row) => row._selected == 'all');
        if (all) return 'all';
        let none = childRows.every((row) => row._selected == 'none');
        if (none) return 'none';
        let some = !all && !none;
        if (some) return 'some';
        // this should exhaust good states
        throw Error('Target selection in a bad state.')
    }
}