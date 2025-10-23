# build.sh
#!/usr/bin/env bash
set -euo pipefail

APP_NAME="MermaidStudio"
ENTRYPOINT="mermaid_studio.py"

# 1. Optional virtualenv for a clean build
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

# 2. Install build dependencies
python -m pip install --upgrade pip
python -m pip install pyinstaller pillow

# 3. Build
# - onefile creates a single self-contained binary
# - windowed removes the terminal window for GUI apps
# - you can add an icon by uncommenting --icon
pyinstaller \
  --noconfirm \
  --onefile \
  --windowed \
  --name "${APP_NAME}" \
  --clean \
  --specpath build \
  mermaid_studio.spec

echo
echo "Build finished."
echo "Binary is at: dist/${APP_NAME}"
echo
echo "Notes"
echo "- Ensure mermaid-cli (mmdc) is installed and reachable by the app."
echo "- If you use a Puppeteer config JSON, keep it at:"
echo "  ~/.config/mermaid_studio/puppeteer.json"
echo "- Example config content:"
echo '  {'
echo '    "executablePath": "/full/path/to/chrome",'
echo '    "args": ["--no-sandbox", "--disable-setuid-sandbox"]'
echo '  }'
echo

# End of build.sh
