# Mermaid Studio (Python UI)

A lightweight desktop GUI for Mermaid diagrams, built with Python + Tkinter.  
It provides a simple two-pane interface: a text editor on the left for Mermaid code and a live rendered preview on the right.

![Mermaid Studio Screenshot](Screenshot.png)

---

## ✨ Features

- Write and edit Mermaid flowcharts, sequence diagrams, and more.
- Render diagrams to PNG with one click (via mermaid-cli).
- Save and open .mmd files.
- Export rendered PNGs.
- Configurable mmdc path.
- Simple, dependency-light Python desktop app (no Electron).

---

## 🧩 Requirements

- Python 3.10+
- Node.js + npm (for installing mermaid-cli)
- A working Chrome or Chromium browser binary (for Puppeteer)
- Pillow Python library (pip install pillow)

---

## ⚙️ Installation

1. Clone the repository

   git clone https://github.com/<yourusername>/mermaid-studio.git  
   cd mermaid-studio

2. Install dependencies

   sudo apt install python3-tk python3-pil python3-pil.imagetk nodejs npm -y  
   pip install pillow

3. Install mermaid-cli globally

   sudo npm install -g @mermaid-js/mermaid-cli

4. Install Chrome for Puppeteer

   npx --yes puppeteer@latest browsers install chrome

5. Create Puppeteer config file

   npx --yes puppeteer@latest browsers install chrome
   CHROME="$(ls -d ~/.cache/puppeteer/chrome/*/chrome-linux64/chrome | tail -n1)"
   mkdir -p ~/.config/mermaid_studio
   cat > ~/.config/mermaid_studio/puppeteer.json <<EOF
   {
   "executablePath": "$CHROME",
   "args": ["--no-sandbox", "--disable-setuid-sandbox"]
   }
   EOF


---

## ▶️ Running

   python3 mermaid_studio.py

When launched, you can:  
- Edit Mermaid code in the left pane.  
- Click "Render" to generate a PNG.  
- Use "File → Save" or "Export PNG As..." as needed.

---

## 🧠 Notes

- If the render button seems to do nothing, check:  
  - Settings → Set mmdc path... points to your actual mmdc binary (for example /usr/local/bin/mmdc).  
  - Your Puppeteer config file (~/.config/mermaid_studio/puppeteer.json) points to a valid Chrome binary.  
- Temporary files are written to ~/mermaid_studio_cache.  
- Output PNGs are rendered next to your .mmd files or in the cache folder.

---

## 🧱 Building a Standalone App (PyInstaller)

You can package Mermaid Studio into a single self-contained binary for Linux using PyInstaller.

1. Ensure build tools are installed:

   sudo apt install python3-venv python3-pip -y  
   pip install pyinstaller pillow

2. Run the included build script:

   chmod +x build.sh  
   ./build.sh

3. The resulting binary will be created at:

   dist/MermaidStudio

4. Notes:
   - The app still relies on your system mermaid-cli (mmdc).  
   - Ensure `@mermaid-js/mermaid-cli` is installed globally and works from the terminal.  
   - If your setup uses a Puppeteer config file, keep it at:  
     ~/.config/mermaid_studio/puppeteer.json  
   - Example config content:  
     {  
       "executablePath": "/full/path/to/chrome",  
       "args": ["--no-sandbox", "--disable-setuid-sandbox"]  
     }

---

## 🪶 License

MIT License © 2025

---

## 💡 Acknowledgements

- Mermaid.js (https://mermaid.js.org/)  
- @mermaid-js/mermaid-cli (https://github.com/mermaid-js/mermaid-cli)  
- Tkinter (Python standard GUI)
