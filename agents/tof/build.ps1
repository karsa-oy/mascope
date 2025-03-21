#Requires -Version 7.0 -PSEdition Core

# create the binary in the virutal env
uv run pyinstaller @(
    'tof_agent.py'
    '--onefile', '--name', 'Mascope-TofAgent'     # make one executable file
    '--noconfirm'                                 # replace dist w/o confirming
    '--console'                                   # open the console for logs
    '--icon=assets/icon.ico'                      # use the Mascope icon
    '--collect-all', 'mascope_tofwerk'            # bundle tofwerk lib
    '--collect-all', 'mascope_runtime'            # bundle runtime lib
    '--collect-all', 'mascope_sdk'                # bundle mascope api wrapper
)
