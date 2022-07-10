process.env.APP_NAME = process.env.npm_package_name;
process.env.APP_VERSION = process.env.npm_package_version;

module.exports = {
  productionSourceMap: false,
}