{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      dotnet = pkgs.dotnetCorePackages.dotnet_9.runtime;
      fhs = pkgs.buildFHSEnv {
        name = "mascope";
        targetPkgs =
          ps: with ps; [
            python312Packages.python-lsp-server
            ruff
            uv
            nodejs_22
            dotnet
            concurrently
            docker_27
            openssl
            gcc
            zlib
          ];
        profile = ''
          export DOTNET_BIN="${dotnet}/bin/dotnet"
          export VIRTUAL_ENV=".venv"
        '';
        runScript = "nu -e 'overlay use .venv/bin/activate.nu'";
      };
    in
    {
      devShells.${system}.default = fhs.env;
    };
}
