# Backlogia v{VERSION} - Desktop Edition

## 🎮 What's New

This release introduces **Desktop Application Mode**, allowing you to run Backlogia as a standalone native application on Windows, macOS, and Linux.

### ✨ Key Features

- **Native Desktop App** - Run Backlogia without opening a browser
- **Elegant Loading Screen** - Beautiful animated startup experience
- **Persistent Data** - Your library and settings are saved locally
- **Auto Port Management** - Handles port conflicts automatically
- **Fast Startup** - Application ready in ~1 second

### 📦 Downloads

Choose the right version for your operating system:

| Platform | Download | Size |
|----------|----------|------|
| 🪟 Windows 10/11 | [Backlogia-Windows.zip](./Backlogia-Windows.zip) | ~35 MB |
| 🍎 macOS 10.15+ | [Backlogia-macOS.tar.gz](./Backlogia-macOS.tar.gz) | ~35 MB |
| 🐧 Linux | [Backlogia-Linux.tar.gz](./Backlogia-Linux.tar.gz) | ~35 MB |

### 🚀 Installation

**Windows:**
1. Download and extract `Backlogia-Windows.zip`
2. Run `Backlogia.exe`
3. If prompted, install [Microsoft Edge WebView2](https://go.microsoft.com/fwlink/p/?LinkId=2124703)

**macOS:**
1. Download and extract `Backlogia-macOS.tar.gz`
2. Right-click `Backlogia` and select "Open" (first time only)
3. Application will start in a native window

**Linux:**
1. Install WebKitGTK: `sudo apt install gir1.2-webkit2-4.0` (Ubuntu/Debian)
2. Download and extract `Backlogia-Linux.tar.gz`
3. Run `./Backlogia`

### 📝 System Requirements

- **Windows:** Windows 10 or later, Edge WebView2 Runtime
- **macOS:** macOS 10.15 (Catalina) or later
- **Linux:** Ubuntu 20.04+ / Fedora 35+ or equivalent, WebKitGTK 2.0

### 🔧 Technical Details

- Data stored in: `%APPDATA%\Backlogia` (Windows), `~/Library/Application Support/Backlogia` (macOS), `~/.config/backlogia` (Linux)
- Logs available in: `<data-dir>/logs/`
- Automatic port allocation (starts at 8000)
- Built with PyWebView + PyInstaller

### 🐛 Known Issues

- None reported yet! Please [report issues](https://github.com/sam1am/backlogia/issues) if you encounter any.

### 📚 Documentation

- [README](https://github.com/sam1am/backlogia#readme)
- [CHANGELOG](https://github.com/sam1am/backlogia/blob/main/CHANGELOG.md)

---

**Full Changelog**: https://github.com/sam1am/backlogia/compare/v0.1.0...v{VERSION}
