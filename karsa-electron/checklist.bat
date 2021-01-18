@ECHO OFF
:: Run this script before 'yarn electron:publish' to make sure all pre-requisits are in place

:: this is to fix a bug in plotly js module
findstr /C:"}.apply(self);" node_modules\plotly.js-dist\plotly.js || (echo Not ready to build karsa-desktop: fix a bug in node_modules\plotly.js-dist\plotly.js!  &&  exit /b 1)

:: GH_TOKEN is a github repository access token 
set GH_TOKEN || (echo Not ready to build karsa-desktop: GH_TOKEN variable was not set && exit /b 1)

echo Ready to build karsa-desktop
exit /b 0