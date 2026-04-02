import os
import subprocess
from datetime import datetime

from tests.config import LOG_PATH


# Generate the current date-time string
datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Save report as xml
# filename = f"report_{datetime_str}.xml"
# command = f"poetry run pytest --junitxml={os.path.join(LOG_PATH, filename)}"

# Save report as txt
filename = f"report_{datetime_str}.log"
command = f"poetry run pytest > {os.path.join(LOG_PATH, filename)}"

# Run the command
subprocess.run(command, shell=True)
