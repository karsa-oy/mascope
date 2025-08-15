# Mascope Tools

**Mascope Tools** is a Python library providing utilities for data processing, analysis, and visualization, designed to support the Mascope platform and related scientific workflows.

## Features

- **Alignment Tools**  
  Utilities for calibration and alignment of datasets.
  - [`alignment/calibration.py`](src/mascope_tools/alignment/calibration.py): Calibration routines and helpers.
  - [`alignment/utils.py`](src/mascope_tools/alignment/utils.py): Supporting functions for alignment tasks.

- **Composition Assignment**  
  Tools for chemical composition analysis and filtering.
  - [`composition/constants.py`](src/mascope_tools/composition/constants.py): Domain-specific constants.
  - [`composition/finder.py`](src/mascope_tools/composition/finder.py): Algorithms for finding chemical compositions.
  - [`composition/heuristic_filter.py`](src/mascope_tools/composition/heuristic_filter.py): Heuristic filters for composition candidates.
  - [`composition/models.py`](src/mascope_tools/composition/models.py): Data models for composition analysis.
  - [`composition/utils.py`](src/mascope_tools/composition/utils.py): Utility functions for composition workflows.

- **Visualization**  
  - [`visualization.py`](src/mascope_tools/visualization.py): Functions for data visualization and plotting.