#Requires -Version 7.0 -PSEdition Core

poetry install --with dev

# create the binary in the virutal env
poetry run pyinstaller @(
    './src/mascope_file_agent/main.py'
    '--onefile', '--name', 'Mascope-File-Agent'   # make one executable file
    '--noconfirm'                                 # replace dist w/o confirming
    '--console'                                   # open the console for logs
    '--icon=assets/icon.ico'                      # use the Mascope icon
    '--collect-all', 'mascope_runtime'            # bundle runtime lib
    '--collect-all', 'mascope_sdk'                # bundle mascope api wrapper
)
