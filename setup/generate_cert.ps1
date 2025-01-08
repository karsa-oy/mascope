# Script to generate a self-signed SSL certificate for testing Mascope "prod" mode
# in local development environment

# Check if certificate already exists
if (Test-Path "${env:MASCOPE_PATH}/secrets/mascope.app.*") {
    Write-Host "Found an existing certificate. Exiting..."
    return
}

# Install OpenSSL
if ( !( Get-Command openssl -ErrorAction SilentlyContinue) ) {
    Write-Host "Installing OpenSSL..."
    winget install --id ShiningLight.OpenSSL
}

# Generate the key
openssl req `
    -x509 `
    -nodes `
    -subj "/CN=mascope.app" `
    -addext "subjectAltName=DNS:mascope.app" `
    -days 365 `
    -newkey rsa:2048 `
    -keyout "${env:MASCOPE_PATH}/secrets/mascope.app.key" `
    -out "${env:MASCOPE_PATH}/secrets/mascope.app.pem"