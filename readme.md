<div align="center">

# ❄️ CryoTask
### Modern App Suspender & RAM Optimizer

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Downloads](https://img.shields.io/github/downloads/GZomeMain/CryoTask/total?style=flat&color=orange)

**Freeze heavy applications to stop CPU usage or Trim their memory to free up RAM.**

[⬇️ Download Latest Version](https://github.com/GZomeMain/CryoTask/releases) • [🐛 Report Bug](https://github.com/GZomeMain/CryoTask/issues)

<br>
<img src="assets/screenshot.png" alt="CryoTask Screenshot" width="700" style="border-radius: 10px; box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);"/>
<br>
<br>

</div>

## 🚀 Overview

**CryoTask** is a lightweight Windows utility designed to give you control over your system resources. Whether you have a game running in the background, a heavy IDE, or a RAM-hungry browser, CryoTask helps you reclaim performance without closing your apps.

It combines the functionality of a **Process Freezer** (pausing execution) and a **Memory Cleaner** (like Mem Reduct) into one modern, dark-themed interface.

## ✨ Features

*   **❄️ Suspend (Freeze) Apps:** Completely pause an application's processes. This drops its CPU usage to **0%**, stopping battery drain and heat generation while keeping the app open.
*   **🧹 Smart RAM Trimming:** Uses native Windows APIs to force applications to release unused memory (Working Set) back to the OS.
*   **🧠 Group Awareness:** Automatically detects multi-process applications (like **Google Chrome, Discord, VS Code**) and manages the entire group at once. No more suspending just the "frame" while the background tabs keep eating RAM.
*   **💾 State Persistence:** Remembers which apps you suspended, even after you close and reopen CryoTask.
*   **🎨 Modern UI:** Built with `CustomTkinter` for a clean, Windows 11-style dark mode interface.
*   **🛡️ Safety Filters:** Only lists applications with visible windows to prevent accidental suspension of critical system services.

## 📥 Installation

### Option 1: Executable (Recommended for Users)
No coding knowledge required.
1.  Go to the [Releases Page](https://github.com/GZomeMain/CryoTask/releases).
2.  Download the latest `CryoTask.zip`.
3.  Extract and run `CryoTask.exe` as **Administrator**.

### Option 2: Run from Source (For Developers)
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/GZomeMain/CryoTask.git
    cd CryoTask
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    *   *Note: You must run your terminal/CMD as Administrator for memory trimming to work.*
    ```bash
    python main.py
    ```

## ⚙️ How it Works

CryoTask interacts directly with the Windows API to perform its functions:

1.  **Suspending:** It utilizes `win32api` and `SuspendThread`. It iterates through every thread of the target process and pauses execution. The OS stops scheduling CPU time for these threads until resumed.
2.  **Trimming:** It calls `psapi.dll` -> `EmptyWorkingSet`. This instructs Windows to move the data currently in the application's RAM (Working Set) to the Pagefile (Disk), freeing up physical RAM for other tasks. The app will reload this data from disk only when needed.

## 🛠️ Build it Yourself

If you want to compile the `.exe` yourself:

1.  Install PyInstaller: `pip install pyinstaller`
2.  Run the included build script:
    ```bash
    python build.py
    ```
3.  The executable will appear in the `dist` folder.

## ⚠️ Disclaimer

While CryoTask filters out system processes, suspending or trimming the memory of unstable applications or active anti-cheat software may cause crashes. **Use responsibly.**

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---
<div align="center">
  <sub>Built with Python & CustomTkinter</sub>
</div>
