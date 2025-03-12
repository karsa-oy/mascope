#Requires -Version 7.0 -PSEdition Core

Param
(
    # Actions: install, update, uninstall, reinstall
    [parameter(mandatory = $true, position = 0)][string]$Action = 'reinstall'
)

# SCRIPT

$Main = {
    $Install = $Action -eq 'install'
    $Reinstall = $Action -eq 'reinstall'
    $Uninstall = $Action -eq 'uninstall'
    $Update = $Action -eq 'update'

    Write-Intro
    
    if ( $Uninstall -or $Reinstall) {
        Uninstall-MascopeModules
        Clear-MascopeEnvVars
    }

    if ( $Install -or $Reinstall ) {    
        Test-ExistingPipx
        Set-MascopeEnvVars
        Install-Tooling
    }
    
    if ( $Install -or $Reinstall -or $Update) {
        Clear-MascopeState
        Install-MascopeModules
    }
    
    Write-Outro
}

# HELPERS

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
    Write-Output @" 
    
    User environment variable ${Key} set to ${Val}
    
"@
}

function Clear-EnvVar {
    param (
        $Key
    )
    [Environment]::SetEnvironmentVariable($Key, $null, 'User')
    Write-Output "    User environment variable ${Key} cleared"
}

# COMMANDS

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

function Set-MascopeEnvVars {
    Write-Output @"

    +------------------------+
    | 📝 SETTING ENV VARS 📝 |
    +------------------------+

"@
    # Set global env var with path to the cloned repo
    Set-EnvVar 'MASCOPE_PATH' (Get-Item $PSScriptRoot).parent.FullName
}

function Clear-MascopeEnvVars {
    Write-Output @"

    +-------------------------+
    | 📝 CLEARING ENV VARS 📝 |
    +-------------------------+

"@
    # Clear global env var
    Clear-EnvVar 'MASCOPE_PATH'
}

function Clear-MascopeState {
    Write-Output @"

    +----------------------+
    | 🗑️ CLEARING STATE 🗑️ |
    +----------------------+

    Deleting runtime/state.json
"@
    $StatePath = "${env:MASCOPE_PATH}/runtime/state.json"
    if (Test-Path $StatePath) {
        Remove-Item $StatePath
    }
}

function Install-Tooling {
    Write-Output @"

    +-------------------------+
    | 🐍 INSTALLING PYTHON 🐍 |
    +-------------------------+

    Installing Python 3.12, Pipx, Poetry and .NET Runtime

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
    # install dotnet runtime (for /libraries/mascope_hardware/orbitrap)
    winget install --silent Microsoft.DotNet.Runtime.9

    Write-Output @"

    +-------------------------+
    | ☕ INSTALLING NODEJS ☕ |
    +-------------------------+

"@
    # install node 22
    winget install --silent OpenJS.NodeJS
    # install concurrently for CLI
    npm install -g concurrently

    Write-Output @"

    +-------------------------+
    | 🐳 INSTALLING DOCKER 🐳 |
    +-------------------------+

"@
    # install docker desktop
    winget install --silent Docker.DockerDesktop
}


function Set-RuntimePermissions {
    Write-Output @"

    +---------------------------------------+
    | ⚡ SETTING RUNTIME ENV PERMISSIONS ⚡ |
    +---------------------------------------+
"@

    $RuntimeEnv = "${env:MASCOPE_PATH}\runtime\env"
    $acl = Get-Acl $RuntimeEnv
    # ensure recursive application
    $acl.SetAccessRuleProtection($true, $false)
    $acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }
    # create rule
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Users", "FullControl", "Allow")
    $acl.AddAccessRule($rule)
    $acl | Set-Acl $RuntimeEnv
    # recurse
    Get-ChildItem -Path $RuntimeEnv -Recurse |  Set-Acl -AclObject $acl
}

function Install-MascopeModules {
    Write-Output @"

    +----------------------------------+
    | 🏗️ INSTALLING MASCOPE MODULES 🏗️ |
    +----------------------------------+

"@
    # remove when warning is resolved
    # https://github.com/open-cli-tools/concurrently/issues/492
    [System.Environment]::SetEnvironmentVariable('NODE_NO_WARNINGS', 1)
    # Install dev dependencies
    py -3.12 "${env:MASCOPE_PATH}/setup/mascope.py" install
}

function Uninstall-MascopeModules {
    Write-Output @"

    +------------------------------------+
    | 🏗️ UNINSTALLING MASCOPE MODULES 🏗️ |
    +------------------------------------+

"@
    # remove when warning is resolved
    # https://github.com/open-cli-tools/concurrently/issues/492
    [System.Environment]::SetEnvironmentVariable('NODE_NO_WARNINGS', 1)
    # Install dev dependencies
    py -3.12 "${env:MASCOPE_PATH}/setup/mascope.py" uninstall
}

# BANNERS


function Write-Intro {
    if ( $Action -eq 'install') {    
        Write-Output @"

    +--------------------------------+
    | 🚀 MASCOPE WINDOWS INSTALL  🚀 |
    +--------------------------------+

    Installing mascope modules
"@
    } 
    if ( $Action -eq 'update') {
        Write-Output @"

    +------------------------------+
    | 🚀 MASCOPE WINDOWS UPDATE 🚀 |
    +------------------------------+

    Updating mascope modules
"@
    }
    if ( $Action -eq 'uninstall') {
        Write-Output @"

    +---------------------------------+
    | 🚀 MASCOPE WINDOWS UNINSTALL 🚀 |
    +---------------------------------+
    
    Uninstalling mascope modules
"@
    }
    if ( $Action -eq 'reinstall') {
        Write-Output @"

    +---------------------------------+
    | 🚀 MASCOPE WINDOWS REINSTALL 🚀 |
    +---------------------------------+
    
    Reinstalling mascope modules
"@
    }
}


function Write-Outro {
    if ( $Action -eq 'install') {    
        Write-Output @"

    +-------------------------------------------+
    | 🎉 MASCOPE WINDOWS INSTALL SUCCESSFUL! 🎉 |
    +-------------------------------------------+

    Run 'mascope --help' and open the README.md for documentation.
"@
    } 
    if ( $Action -eq 'update') {
        Write-Output @"

    +------------------------------------------+
    | 🎉 MASCOPE WINDOWS UPDATE SUCCESSFUL! 🎉 |
    +------------------------------------------+

    Run 'mascope --help' and open the README.md for documentation.
"@
    }
    if ( $Action -eq 'uninstall') {
        Write-Output @"

    +---------------------------------------------+
    | 🎉 MASCOPE WINDOWS UNINSTALL SUCCESSFUL! 🎉 |
    +---------------------------------------------+


"@
    }
    if ( $Action -eq 'reinstall') {
        Write-Output @"

    +---------------------------------------------+
    | 🎉 MASCOPE WINDOWS REINSTALL SUCCESSFUL! 🎉 |
    +---------------------------------------------+

    Run 'mascope --help' and open the README.md for documentation.
"@
    }
}

# ENTRYPOINT

& $Main
