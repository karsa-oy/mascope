{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      fhs = pkgs.buildFHSEnv {
        name = "fhs-shell";
        targetPkgs =
          ps: with ps; [
            python312Full
            python312Packages.pipx
            poetry
            nodejs_22
            dotnetCorePackages.dotnet_9.runtime
            concurrently
            docker_27
          ];
        profile = ''
          pipx ensurepath
          PIPX_DEFAULT_PYTHON=/usr/bin/python
          export PIPX_DEFAULT_PYTHON
        '';
      };
    in
    {
      devShells.${system}.default = fhs.env;
    };
}
