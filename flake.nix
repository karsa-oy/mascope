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
        name = "fhs-shell";
        targetPkgs =
          ps: with ps; [
            python312Full
            python312Packages.pipx
            poetry
            nodejs_22
            dotnet
            concurrently
            docker_27
          ];
        profile = ''
          pipx ensurepath
          export PIPX_DEFAULT_PYTHON=/usr/bin/python
          export DOTNET_BIN="${dotnet}/bin/dotnet"
        '';
      };
    in
    {
      devShells.${system}.default = fhs.env;
    };
}
