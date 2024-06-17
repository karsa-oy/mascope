# Backend docs

Backend documentation can be built into html from python docstrings automatically, using [sphinx](https://www.sphinx-doc.org/en/master/).

```
docs
├──build
│  ├───doctrees         # Backend documentation doctrees
│  └───html             # Backend documentation in html format
├──source               # Backend documentation source
│  ├───conf.py          # Sphinx configuration file
│  ├───index.rst        # Documentation index
│  └───modules.rst      # Documentation modules
└───update_docs.bat     # Script to rebuild documentation
```

### Read

Documentation is available at `backend/docs/build/html/index.html`

### Edit

Main files to configure how documentation is built are: `source/conf.py`, `source/index.rst` and `source/modules.rst`. After editing, rebuild the docs as instructed below.

### Build

To update documentation, run from backend root `docs\update_docs.bat`.
