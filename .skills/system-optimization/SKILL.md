---
name: System Optimization & Robustness
description: Technical workflow for improving the stability, performance, and accuracy of process management and memory operations.
---

# ⚙️ System Optimization & Robustness Skill

This skill provides deep technical guidance on interacting with the Windows API safely and efficiently to manage system resources.

## 🛡️ Stability & Safety
- **Exception Handling**: Wrap every WinAPI call (`OpenProcess`, `SuspendThread`, `EmptyWorkingSet`) in robust try-except blocks.
- **Permission Elevation**: Proactively check for `ctypes.windll.shell32.IsUserAnAdmin()` and handle the "Access Denied" (0x5) error gracefully.
- **Critical Process Filtering**: Maintain a strict blacklist (hardcoded + configurable) to prevent freezing `wininit.exe`, `lsass.exe`, or `services.exe`.

## 🚀 Performance Tuning
- **Threaded Refresh**: Do NOT run `psutil.process_iter()` on the UI thread. Use a `threading.Thread` or `concurrent.futures.ThreadPoolExecutor` to keep the UI fluid.
- **Batch Operations**: When applying a preset with 10+ apps, batch the operations to avoid UI stutter.
- **Resource Sampling**: Cache process icons and metadata. Only update CPU usage and RAM stats every 1-2 seconds to reduce the overhead of CryoTask itself.

## 🔬 Precision Trimming
- **Working Set API**: Beyond `EmptyWorkingSet`, consider exploring `SetProcessWorkingSetSize` for more granular control if users request "Advanced Mode" tuning.
- **Verification**: Always verify the result of a Trim operation by sampling the RAM usage immediately after the call (expect a significant drop).

## 🧪 Testing Strategies
- **Mock Environment**: Create a script that spawns "dummy" low-priority processes to test Suspend/Resume logic without risking system stability.
- **Stress Test**: Test the "Periodic Trim" feature over a 24-hour period to ensure no memory leaks exist within CryoTask.

---
*Created by Antigravity - Optimized for CryoTask Upgrade.*
