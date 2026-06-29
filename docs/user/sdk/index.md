# SDK & API

Load and analyse Mascope data from Python (notebooks or scripts).

```sh
pip install mascope_sdk
```

```python
from mascope_sdk import MascopeClient

mascope = MascopeClient(workspace="My Workspace")
peaks = mascope.load_peaks(dataset="My Dataset", batches="Uronium")
```

Full reference, configuration, and tutorial notebooks: see the SDK readme
(`libraries/sdk/README.md`).

<!-- TODO Phase 3: publish the SDK README content into this section as the single
source, or keep this page thin and deep-link. See the roadmap. -->
