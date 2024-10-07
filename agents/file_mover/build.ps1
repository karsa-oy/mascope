#Requires -Version 7.0 -PSEdition Core

# ensure the virtual env is up-to-date
poetry install

# create the binary in the virutal env
poetry run pyinstaller @(
    'file_mover.py'
    '--onefile', '--name', 'Mascope-FileMover'     # make one executable file
    '--noconfirm'                                 # replace dist w/o confirming
    '--console'                                   # open the console for logs
    '--icon=assets/icon.ico'                      # use the Mascope icon
    '--collect-all', 'mascope_runtime'            # bundle runtime lib
)