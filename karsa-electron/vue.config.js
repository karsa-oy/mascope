process.env.APP_NAME = process.env.npm_package_name;
process.env.APP_VERSION = process.env.npm_package_version;

module.exports = {
    productionSourceMap: false,
    pluginOptions: {
      electronBuilder: {
        builderOptions: {
          // options placed here will be merged with default configuration and passed to electron-builder
          appId: "karsa_desktop.com",
          publish: ['github'],
          win: {
            // icon: "public/img/k.ico",
            icon: "public/img/icon256x256.png",
            target: "nsis",     //target should be nsis for autoupdate
            certificateFile: "cert/karsa_cacert.pfx",   //alt: use CSC_LINK env.var.
            certificatePassword: "",                    //alt: use CSC_KEY_PASSWORD env.var.
            publisherName: "www.karsa.fi",
            verifyUpdateCodeSignature: false,   //bug workaround: https://github.com/electron-userland/electron-builder/issues/1856
          },
          files: [
            "**/*"
          ],
          extraFiles: [
            {
                "from": ".env",
                "to": ".env",
                "filter": ["**/*"]
            },
            {
              "from": "configs",
              "to": "configs",
              "filter": ["**/*"]
            },
            // {
            //     "from": "py",
            //     "to": "py",
            //     "filter": ["**/*"]
            // },
            // {
            //     "from": "py_code",
            //     "to": "py_code",
            //     "filter": ["**/*"]
            // }
          ]
        }
      }
    }
  }