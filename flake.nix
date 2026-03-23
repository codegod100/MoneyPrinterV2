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
            export UV_PYTHON="${python}/bin/python"
            export UV_PYTHON_DOWNLOADS=never
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib pkgs.zlib ]}:''${LD_LIBRARY_PATH:-}"
            export GECKODRIVER_PATH="${pkgs.geckodriver}/bin/geckodriver"
            export FIREFOX_BIN="${pkgs.firefox}/bin/firefox"
            export IMAGEMAGICK_BINARY="${pkgs.imagemagick}/bin/magick"
            export MPV2_FIREFOX_PROFILE_DIR="$HOME/.mozilla/firefox/moneyprinterv2.default"

            if [ -f "$HOME/.nix-profile/etc/profile.d/hm-session-vars.sh" ]; then
              . "$HOME/.nix-profile/etc/profile.d/hm-session-vars.sh"
            fi

            if [ -z "''${ASSEMBLYAI_API_KEY_FILE:-}" ] && [ -f /run/agenix/assemblyai_api_key ]; then
              export ASSEMBLYAI_API_KEY_FILE=/run/agenix/assemblyai_api_key
            fi

            if [ -z "''${ASSEMBLYAI_API_KEY_FILE:-}" ] && [ -n "''${XDG_RUNTIME_DIR:-}" ] && [ -f "$XDG_RUNTIME_DIR/agenix/assemblyai_api_key" ]; then
              export ASSEMBLYAI_API_KEY_FILE="$XDG_RUNTIME_DIR/agenix/assemblyai_api_key"
            fi

            if [ -z "''${ZAI_API_KEY_FILE:-}" ] && [ -f /run/agenix/zai_api_key ]; then
              export ZAI_API_KEY_FILE=/run/agenix/zai_api_key
            fi

            if [ -z "''${ZAI_API_KEY_FILE:-}" ] && [ -n "''${XDG_RUNTIME_DIR:-}" ] && [ -f "$XDG_RUNTIME_DIR/agenix/zai_api_key" ]; then
              export ZAI_API_KEY_FILE="$XDG_RUNTIME_DIR/agenix/zai_api_key"
            fi

            if [ ! -f config.json ]; then
              cp config.example.json config.json
              echo "[nix] Created config.json from config.example.json"
            fi

            mkdir -p "$MPV2_FIREFOX_PROFILE_DIR"
            export FIREFOX_PROFILE="$MPV2_FIREFOX_PROFILE_DIR"

            if [ ! -d venv ]; then
              uv venv --python "$UV_PYTHON" venv
              echo "[nix] Created uv-managed venv with Python 3.12"
            fi

            . venv/bin/activate
            export VIRTUAL_ENV="$PWD/venv"
            export PATH="$VIRTUAL_ENV/bin:$PATH"

            "$VIRTUAL_ENV/bin/python" - <<'PY'
import json
import os

cfg_path = "config.json"
profile_path = os.environ.get("FIREFOX_PROFILE", "").strip()

if profile_path and os.path.exists(cfg_path):
    with open(cfg_path, "r", encoding="utf-8") as file:
        cfg = json.load(file)

    if not str(cfg.get("firefox_profile", "")).strip():
        cfg["firefox_profile"] = profile_path
        with open(cfg_path, "w", encoding="utf-8") as file:
            json.dump(cfg, file, indent=2)
            file.write("\n")
        print(f"[nix] Set firefox_profile in config.json: {profile_path}")
PY

            REQUIREMENTS_STAMP="venv/.requirements.txt.stamp"
            CURRENT_REQUIREMENTS_HASH="$(sha256sum requirements.txt | awk '{print $1}')"
            SAVED_REQUIREMENTS_HASH=""
            NEEDS_INSTALL=0

            if [ -f "$REQUIREMENTS_STAMP" ]; then
              SAVED_REQUIREMENTS_HASH="$(cat "$REQUIREMENTS_STAMP")"
            fi

            if [ "$CURRENT_REQUIREMENTS_HASH" != "$SAVED_REQUIREMENTS_HASH" ]; then
              NEEDS_INSTALL=1
            fi

            if ! "$VIRTUAL_ENV/bin/python" -c "import requests" >/dev/null 2>&1; then
              NEEDS_INSTALL=1
            fi

            if [ "$NEEDS_INSTALL" -eq 1 ]; then
              echo "[nix] Installing Python dependencies from requirements.txt"
              uv pip install --python "$VIRTUAL_ENV/bin/python" -r requirements.txt
              printf '%s\n' "$CURRENT_REQUIREMENTS_HASH" > "$REQUIREMENTS_STAMP"
            fi

            echo "[nix] MoneyPrinterV2 shell ready"
            echo "[nix] Python: $(python --version)"
            echo "[nix] Firefox profile: $FIREFOX_PROFILE"
            if [ -n "''${ASSEMBLYAI_API_KEY_FILE:-}" ]; then
              echo "[nix] AssemblyAI key file: $ASSEMBLYAI_API_KEY_FILE"
            fi
            if [ -n "''${ZAI_API_KEY_FILE:-}" ]; then
              echo "[nix] Z.ai key file: $ZAI_API_KEY_FILE"
            fi
            echo "[nix] Next step: python3 scripts/preflight_local.py"
          '';
        };
      });
}
