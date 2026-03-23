{
  description = "Development shell for MoneyPrinterV2";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };

        python = pkgs.python312;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python
            uv
            python312Packages.pip
            python312Packages.setuptools
            python312Packages.wheel
            python312Packages.virtualenv
            ffmpeg
            imagemagick
            firefox
            geckodriver
            espeak-ng
            git
            curl
          ];

          shellHook = ''
            export PIP_DISABLE_PIP_VERSION_CHECK=1
            export PYTHONNOUSERSITE=1
            export GECKODRIVER_PATH="${pkgs.geckodriver}/bin/geckodriver"
            export FIREFOX_BIN="${pkgs.firefox}/bin/firefox"
            export IMAGEMAGICK_BINARY="${pkgs.imagemagick}/bin/magick"

            if [ ! -f config.json ]; then
              cp config.example.json config.json
              echo "[nix] Created config.json from config.example.json"
            fi

            if [ ! -d venv ]; then
              ${python}/bin/python -m venv venv
              echo "[nix] Created venv with Python 3.12"
            fi

            . venv/bin/activate

            echo "[nix] MoneyPrinterV2 shell ready"
            echo "[nix] Python: $(python --version)"
            echo "[nix] Next step: pip install -r requirements.txt"
          '';
        };
      });
}
