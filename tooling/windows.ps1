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

    Write-Section("MASCOPE ${$Action.ToUpper()}")

    Write-Line("Launching setup script in ${$Action} mode")
    
    if ( $Uninstall -or $Reinstall) {
        Uninstall-Mascope
        Clear-EnvVars
    }

    if ( $Install -or $Reinstall ) {    
        Set-EnvVars
        Install-Tooling
    }
    
    if ( $Install -or $Reinstall) {
        Clear-State
        Install-Mascope
    }

    Write-Section("MASCOPE ${$Action.ToUpper()} SUCCESSFUL!")
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

function Set-EnvVars {
    # Set global env var with path to the cloned repo
    Set-EnvVar 'MASCOPE_PATH' (Get-Item $PSScriptRoot).parent.FullName
}

function Clear-EnvVars {
    # Clear global env var
    Clear-EnvVar 'MASCOPE_PATH'
}

function Clear-State {
    $StatePath = "${env:MASCOPE_PATH}\.runtime\state.json"
    if (Test-Path $StatePath) {
        Remove-Item $StatePath
    }
}

function Install-Tooling {
    Write-Section("INSTALLING TOOLING")
    # install uv
    winget install --id=astral-sh.uv  -e;
    # install dotnet runtime (for mascope_thermo)
    winget install --silent Microsoft.DotNet.Runtime.9
    # install node 22
    winget install --silent OpenJS.NodeJS
    # install concurrently for CLI
    npm install -g concurrently
    # install docker desktop
    winget install --silent Docker.DockerDesktop
    # refresh path so that bins are available in script
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}


function Set-RuntimePermissions {
    Write-Section("SETTING RUNTIME PERMISSSIONS")
    # get access control list
    $RuntimeEnv = "${env:MASCOPE_PATH}\.runtime\env"
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

function Install-Mascope {
    Write-Section("INSTALLING MASCOPE VENV")
    
    uv sync
}

function Uninstall-Mascope {
    Write-Section("UNINSTALLING MASCOPE VENV")

    Remove-Item -Path "${env:MASCOPE_PATH}\.venv" -Recurse
    Remove-Item -Path "${env:MASCOPE_PATH}\server\frontend\node_modules" -Recurse
}

# PRINTING

function Write-Section {
    param (
        $Title
    )
    Write-Output @"

    [$Title]
"@
}

function Write-Line {
    param (
        $Line
    )
    Write-Output @"
    $Line
"@
}

# ENTRYPOINT

& $Main
