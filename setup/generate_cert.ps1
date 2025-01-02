# generate self-signed certificate
if (Test-Path "${env:MASCOPE_PATH}/secrets/mascope.app.*") {
    Write-Host "Found an existing certificate. Exiting..."
    return
 }
openssl req `
    -x509 `
    -nodes `
    -subj "/CN=mascope.app" `
    -addext "subjectAltName=DNS:mascope.app" `
    -days 90 `
    -newkey rsa:2048 `
    -keyout "${env:MASCOPE_PATH}/secrets/mascope.app.key" `
    -out "${env:MASCOPE_PATH}/secrets/mascope.app.pem"