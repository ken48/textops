#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=${WARMPY_PYTHON:?Set WARMPY_PYTHON explicitly}
IFS=$'\n\t'

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <deps_yaml_or_dir>"
  exit 1
fi

INPUT="$1"

if [[ -f "$INPUT" ]]; then
  DEPS_YAML="$INPUT"
elif [[ -d "$INPUT" ]]; then
  DEPS_YAML="$INPUT/warmpy.yaml"
else
  echo "ERROR: input not found: $INPUT"
  exit 1
fi

DEPS_YAML="$(cd "$(dirname "$DEPS_YAML")" && pwd)/$(basename "$DEPS_YAML")"
cd "$SCRIPT_DIR"

BUILD_DIR="$SCRIPT_DIR/.build"
VENV_DIR="$BUILD_DIR/venv"
PIP_DEPS_TXT="$BUILD_DIR/pip_deps.txt"
EXTRA_INCLUDES_JSON="$BUILD_DIR/extra_includes.json"
WARMUP_JSON="$BUILD_DIR/warmup.json"

build_icns() {
  local icon_png="$SCRIPT_DIR/assets/warmpy_icon.png"
  local icns_out="$SCRIPT_DIR/assets/warmpy.icns"
  local iconset_dir="$BUILD_DIR/warmpy.iconset"

  if ! command -v iconutil >/dev/null 2>&1; then
    echo "iconutil not found, keeping existing assets/warmpy.icns"
    return 0
  fi
  if ! command -v sips >/dev/null 2>&1; then
    echo "sips not found, keeping existing assets/warmpy.icns"
    return 0
  fi

  rm -rf "$iconset_dir"
  mkdir -p "$iconset_dir"

  for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$icon_png" --out "$iconset_dir/icon_${size}x${size}.png" >/dev/null
    sips -z $((size * 2)) $((size * 2)) "$icon_png" --out "$iconset_dir/icon_${size}x${size}@2x.png" >/dev/null
  done

  iconutil -c icns "$iconset_dir" -o "$icns_out" >/dev/null
}

echo "== WarmPy build =="
echo "project_dir : $SCRIPT_DIR"
echo "deps_input  : $INPUT"
echo "deps_yaml   : $DEPS_YAML"
echo

if [[ ! -f "$DEPS_YAML" ]]; then
  echo "ERROR: deps yaml not found: $DEPS_YAML"
  exit 1
fi

rm -rf "$BUILD_DIR" dist build
mkdir -p "$BUILD_DIR"

build_icns

"$PYTHON" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel
python -m pip install setuptools py2app pillow pyyaml pyobjc-framework-Cocoa

python - <<PY
import json
from pathlib import Path
import yaml

deps_path = Path(r"$DEPS_YAML")
build_dir = Path(r"$BUILD_DIR")
pip_out = Path(r"$PIP_DEPS_TXT")
inc_out = Path(r"$EXTRA_INCLUDES_JSON")
warmup_out = Path(r"$WARMUP_JSON")

data = yaml.safe_load(deps_path.read_text(encoding="utf-8")) or {}

pip_deps = data.get("pip") or []
modules = data.get("modules") or []

for key, val in [("pip", pip_deps), ("modules", modules)]:
    if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
        raise SystemExit(f"ERROR: '{key}' must be a list of strings")

pip_deps = [x.strip() for x in pip_deps if x.strip()]
modules = [x.strip() for x in modules if x.strip()]

dedup_modules = list(dict.fromkeys(modules))

build_dir.mkdir(parents=True, exist_ok=True)
pip_out.write_text("\n".join(pip_deps) + ("\n" if pip_deps else ""), encoding="utf-8")
inc_out.write_text(json.dumps(dedup_modules, indent=2), encoding="utf-8")
warmup_out.write_text(json.dumps({"modules": dedup_modules}, indent=2), encoding="utf-8")
PY

if [[ -s "$PIP_DEPS_TXT" ]]; then
  python -m pip install -r "$PIP_DEPS_TXT"
fi

python setup.py py2app

APP_PATH="$BUILD_DIR/dist/warmpy.app"
if [[ -d "$BUILD_DIR/dist/main.app" ]]; then
  mv "$BUILD_DIR/dist/main.app" "$APP_PATH"
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: expected app bundle not found: $APP_PATH"
  exit 1
fi

if [[ -f "$APP_PATH/Contents/MacOS/main" ]]; then
  mv "$APP_PATH/Contents/MacOS/main" "$APP_PATH/Contents/MacOS/warmpy"
fi

PLIST="$APP_PATH/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleExecutable warmpy" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleExecutable string warmpy" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleName warmpy" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleName string warmpy" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName warmpy" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string warmpy" "$PLIST"

RES_DIR="$APP_PATH/Contents/Resources"
mkdir -p "$RES_DIR"

while IFS= read -r bin; do
  codesign --force --sign - "$bin"
done < <(
  find "$APP_PATH" -type f \( \
    -name "*.so" -o \
    -name "*.dylib" -o \
    -path "*/Contents/MacOS/*" -o \
    -path "*/Contents/Frameworks/Python.framework/Versions/*/Python" \
  \) | sort
)

codesign --force --sign - "$APP_PATH"
codesign --verify --deep --strict --verbose=4 "$APP_PATH"

echo "Build complete: $APP_PATH"
