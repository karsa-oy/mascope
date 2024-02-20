@echo off

set SCRIPT="%TEMP%\%RANDOM%-%RANDOM%-%RANDOM%-%RANDOM%.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%

echo sLinkFile2 = "%cd%\MascopeAgent.lnk" >> %SCRIPT%
echo Set oLink2 = oWS.CreateShortcut(sLinkFile2) >> %SCRIPT%
echo oLink2.TargetPath = "%cd%\run.cmd" >> %SCRIPT%
echo oLink2.IconLocation = "%cd%\bin.exe" >> %SCRIPT%
echo oLink2.WorkingDirectory = "%cd%" >> %SCRIPT%
echo oLink2.Save >> %SCRIPT%

echo sLinkFile1 = "%USERPROFILE%\Desktop\MascopeAgent.lnk" >> %SCRIPT%
echo Set oLink1 = oWS.CreateShortcut(sLinkFile1) >> %SCRIPT%
echo oLink1.TargetPath = "%cd%\run.cmd" >> %SCRIPT%
echo oLink1.IconLocation = "%cd%\bin.exe" >> %SCRIPT%
echo oLink1.WorkingDirectory = "%cd%" >> %SCRIPT%
echo oLink1.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%