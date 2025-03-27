#Requires -Version 7.0 -PSEdition Core


# SCRIPT

$Main = {

    Test-ExistingPipx
    Install-Tooling

}


# HELPERS

function Test-CommandExists {
    param (
        $Cmd
    )
    Get-Command $Cmd -ErrorAction SilentlyContinue
}

function Test-ExistingPipx {
    Write-Output @"

    +----------------------------------+
    | 🔎 CHECKING PIPX INSTALLATION 🔎 |
    +----------------------------------+

"@
    $PythonPath = "${env:UserProfile}\AppData\Local\Programs\Python\Python312\python.exe"
    if ( (Test-CommandExists -Cmd pipx)) {
        Write-Output @"
    pipx detected on your system

"@

        if ( $env:PIPX_DEFAULT_PYTHON -ne $PythonPath ) {
            $title = "  pipx detected in the system"
            $question = @"
    The installer needs to set the default Python version used by pipx.
    
    Do you want to continue?


"@
            $choices = "&Yes, proceed and reconfigure pipx", "&No, abort the installation"
            $decision = $Host.UI.PromptForChoice($title, $question, $choices, 0)
            if ($decision -eq 1) {
                Write-Host "Installation aborted, no changes were made."
                Exit
            }
        }
        else {
            Write-Output @"
    pipx uses the correction version of Python; no further configuration needed.
    
"@  
        }
    }
    else {
        Write-Output @"
    pipx not detected on your system, the installer will set it up.

"@  
    }
}
function Install-Tooling {
    Write-Output @"

    +---------------------------+
    | 🐍 INSTALLING TOOLING 🐍 |
    +---------------------------+

    Installing Python 3.12, Pipx and Poetry

"@
    # install python 3.12
    winget install --silent Python.Python.3.12
    # ensure pipx is available
    if ( !( Test-CommandExists pipx) ) {
        py -3.12 -m pip install --user pipx
        py -3.12 -m pipx ensurepath
    }
    # ensure pipx uses python 3.12
    $PythonPath = "${env:UserProfile}\AppData\Local\Programs\Python\Python312\python.exe"
    if ( !($env:PIPX_DEFAULT_PYTHON -eq $PythonPath) ) {
        Set-EnvVar 'PIPX_DEFAULT_PYTHON' $PythonPath
    }
    # install poetry with pipx
    pipx install poetry
}

# ENTRYPOINT

& $Main