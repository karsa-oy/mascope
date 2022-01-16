const fs = require('fs');
const envfile = require('envfile');

export function readDotenv() {
    let envString = fs.readFileSync('.env');
    return envfile.parse(envString);
}

export function writeDotenv(dotenv) {
    let env_string = envfile.stringify(dotenv);
    fs.writeFileSync('.env', env_string);
}