start cmd /k ""py\App\Python\python.exe" "py_code\TOFService.py""

::start cmd /k ""py\App\Python\python.exe" "py_code\SignalProcessorService.py""

start cmd /k ""py\App\Python\python.exe" "py_code\FileService.py""

start cmd /k ""py\App\Python\python.exe" "py_code\DataVizService.py""

:: start Router locally, if not already running
powershell Test-NetConnection 127.0.0.1 -p 5010 | find /i "failed" && start cmd /k ""py\App\Python\python.exe" "py_code\Router.py""

start cmd /k "yarn electron:serve"