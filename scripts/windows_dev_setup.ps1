#Requires -Version 7.0 -PSEdition Core

$Main = {
    Write-Output @"

    +-----------------------------------------+
    | 🚀 MASCOPE WINDOWS DEV ENV INSTALLER 🚀 |
    +-----------------------------------------+

    Installs everything a Mascope dev needs to get up and running.

"@

    Test-ExistingPipx
    Set-MascopeEnvVars
    Install-Tooling
    Install-MascopeCli
    Install-MascopeDevEnv

    
    Write-Output @"

    +-------------------------------+
    | 🎉 INSTALLATION SUCCESSFUL!🎉 |
    +-------------------------------+

    Run 'mascope --help' and open the README.md for documentation.

"@
}

function Test-CommandExists {
    param (
        $Cmd
    )
    Get-Command $Cmd -ErrorAction SilentlyContinue
}

function Set-EnvVar {
    param (
        $Key,
        $Val
    )
    # Sets environment variable permenantly
    # in the User scope, as well as setting it
    # in the script's scope
    [Environment]::SetEnvironmentVariable($Key, $Val, 'User')
    [Environment]::SetEnvironmentVariable($Key, $Val)
    Write-Output "  User environment variable ${Key} set to ${Val}"
}

function Test-ExistingPipx {
    Write-Output @"

    +-------------------------------------------+
    | 🔎 CHECKING EXISTING PIPX INSTALLATION 🔎 |
    +-------------------------------------------+

"@

    if ( Test-CommandExists -Cmd pipx ) {
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
}

function Set-MascopeEnvVars {
    Write-Output @"

    +------------------------+
    | 📝 SETTING ENV VARS 📝 |
    +------------------------+

"@
    # Set global env var with path to the cloned repo
    Set-EnvVar 'MASCOPE_REPO_PATH' (Get-Item $PSScriptRoot).parent.FullName
}

function Install-Tooling {
    Write-Output @"

    +---------------------------------+
    | 🐍 Installing Python Tooling 🐍 |
    +---------------------------------+

"@
    # install python 3.12
    winget install --silent Python.Python.3.12
    # ensure pipx is available
    if ( !( Test-CommandExists pipx) ) {
        py -3.12 -m pip install --user pipx
        py -3.12 -m pipx ensurepath
    }
    # install poetry with pipx in our python
    Set-EnvVar 'PIPX_DEFAULT_PYTHON' "C:\Users\${env:UserName}\AppData\Local\Programs\Python\Python312\python.exe"
    Set-EnvVar 'MASCOPE_PYTHON_PATH' "C:\Users\${env:UserName}\AppData\Local\Programs\Python\Python312\python.exe"
    pipx install poetry
    Write-Output @"

    +---------------------------------+
    | ☕ Installing NodeJS Tooling ☕ |
    +---------------------------------+

"@
    # install node 22
    winget install --silent OpenJS.NodeJS
    # install concurrently for CLI
    npm install -g concurrently
}

function Install-MascopeCli {
    Write-Output @"

    +------------------------------+
    | ⚡ INSTALLING MASCOPE CLI ⚡ |
    +------------------------------+

"@
    # Mascope Development CLI
    # see /scripts/cli
    Set-Location "${env:MASCOPE_REPO_PATH}\scripts\cli"
    # poetry build
    if (Test-CommandExists mascope) {
        Write-Output "mascope cli detected - reinstalling"
        poetry env use $env:MASCOPE_PYTHON_PATH
        poetry build
        pipx reinstall mascope_cli
    }
    else {
        Write-Output "mascope cli not detected - installing"
        poetry env use $env:MASCOPE_PYTHON_PATH
        poetry build
        pipx install .
    }
    Set-Location $env:MASCOPE_REPO_PATH
}

function Install-MascopeDevEnv {
    Write-Output @"

    +----------------------------------+
    | 🏗️ Installing Mascope Dev Env 🏗️ |
    +----------------------------------+

"@
    # remove when warning is resolved
    # https://github.com/open-cli-tools/concurrently/issues/492
    [System.Environment]::SetEnvironmentVariable('NODE_NO_WARNINGS', 1)
    # Install dev dependencies
    mascope dev install
}

& $Main