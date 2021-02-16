@ECHO OFF
:: Run this script before 'yarn electron:publish' to make sure all pre-requisits are in place

:: this is to fix a bug in plotly js module
findstr /C:"}.apply(self);" node_modules\plotly.js-dist\plotly.js || (echo Not ready to build karsa-desktop: fix a bug in node_modules\plotly.js-dist\plotly.js! - see ..\docs\frontend.html at 'Compiling and Making installer file' section &&  exit /b 1)

:: GH_TOKEN is a github repository access token 
set GH_TOKEN || (echo Not ready to publish karsa-desktop: GH_TOKEN variable was not set && exit /b 1)

:: signed certificate to sign a binary
if not exist "cert\karsa_cacert.pfx" (echo Not ready to publish karsa-desktop: cert\karsa_cacert.pfx missing && exit /b 1)

echo Ready to build and publish karsa-desktop
exit /b 0