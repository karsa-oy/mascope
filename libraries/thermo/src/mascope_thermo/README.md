We leverage [Thermo libraries](https://github.com/thermofisherlsms/RawFileReader/tree/main) to read *.raw files.

The libraries are .NET-based. The problem with .NET imports is that references are not propagated across python files. That means if we do:

```Python
# thermo.py
...
clr.AddReference("ThermoFisher.CommonCore.RawFileReader")
from ThermoFisher.CommonCore.RawFileReader import RawFileAdapter
```

and then try to import `thermo.py` in some other py-file:

```Python
# file_func.py
from mascope_thermo.orbitrap import thermo
```
We will get an error:

> ModuleNotFoundError: No module named 'ThermoFisher'

To avoid this, .NET references must be added to the target file that uses functions from `mascope_thermo.orbitrap`:

```Python
# file_func.py
from pythonnet import load

load("coreclr")
import clr
import mascope_thermo

sys.path.append(os.path.join(mascope_thermo.__path__[0], "./orbitrap/lib/dlls"))

clr.AddReference("ThermoFisher.CommonCore.RawFileReader")
```
