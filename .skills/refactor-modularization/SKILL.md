---
name: Refactor & Modularization
description: Comprehensive workflow for breaking down large monolith files into a clean, maintainable, and modular architecture.
---

# 🏗️ Refactor & Modularization Skill

This skill provides a systematic approach to decomposing monolithic Python applications (like `main.py`) into a structured package with clearly defined responsibilities.

## 🎯 Objectives
- Improve code scanability and maintainability.
- Separate UI logic (CustomTkinter) from system-level logic (Windows API/Process management).
- Implement clean dependency injection where possible.
- Ensure state persistence is handled centrally.

## 🛠️ Step-by-Step Workflow

### 1. Analysis phase
Before moving any code, analyze the existing monolith:
- Identify **Core Logic** (Process freezing, memory trimming).
- Identify **State Management** (Pinned apps, scheduled actions, presets).
- Identify **UI Components** (Custom widgets, main window layout).
- Identify **Utility Functions** (Logging, file I/O, formatting).

### 2. Infrastructure Setup
Create the standard package structure:
```bash
src/
  cryotask/
    __init__.py
    core/             # System-level operations (Suspend/Trim)
    ui/               # UI Components and Main Window
    models/           # Data structures (Presets, Process Info)
    utils/            # Helpers
    persistence/      # JSON storage logic
```

### 3. Extraction Strategy
Extract code in the following order to minimize breakage:
1.  **Constants & Utils**: Move strings and simple helper functions first.
2.  **Core Logic**: Extract the `win32api` and `psutil` calls into a `ProcessManager` class.
3.  **Persistence**: Extract the `.json` loading/saving logic.
4.  **UI Components**: Break down the large `App` class into smaller `frame` or `widget` classes.

### 4. Integration & Testing
- Use a slim `main.py` (or `src/cryotask/cli.py`) as the entry point.
- Verify through logs that system operations (Suspend/Resume/Trim) still have Administrator privileges.
- Check that `assets/` are still correctly resolved via `sys._MEIPASS` (for PyInstaller compatibility).

## ⚠️ Critical Rules
- **Maintain PyInstaller Compatibility**: Ensure the `build.py` and `.spec` files are updated to reflect the new structure.
- **Administrator Context**: Keep in mind that many functions *require* elevated privileges.
- **Global State**: Avoid global variables during refactoring; use a shared `context` or `state` object.

---
*Created by Antigravity - Optimized for CryoTask Upgrade.*
