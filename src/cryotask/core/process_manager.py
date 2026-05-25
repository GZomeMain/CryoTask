import psutil
import ctypes
import win32api
import win32process
import win32con
import win32gui
from collections import defaultdict

from src.cryotask.persistence.storage import save_suspended_state
from src.cryotask.utils.constants import EXCLUDED_PROCESSES, CRITICAL_SYSTEM_PROCESSES

# --- Low Level Windows API ---
psapi = ctypes.WinDLL('psapi.dll')
kernel32 = ctypes.WinDLL('kernel32.dll')
ntdll = ctypes.WinDLL('ntdll.dll')

PROCESS_SET_QUOTA = 0x0100
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SUSPEND_RESUME = 0x0800

def trim_pid(pid):
    try:
        handle = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle: return False
        try:
            result = psapi.EmptyWorkingSet(handle)
        finally:
            kernel32.CloseHandle(handle)
        return bool(result)
    except: return False

def get_process_group_memory(proc_name):
    """Get total private memory for a process group.
    Uses 'private' (Private Bytes) instead of 'rss' (Working Set) to avoid
    double-counting shared memory pages (DLLs) across processes in a group."""
    total_mem = 0
    try:
        for p in psutil.process_iter(['name', 'memory_info']):
            try:
                if p.info['name'] == proc_name:
                    mem_info = p.info['memory_info']
                    total_mem += getattr(mem_info, 'private', mem_info.rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except: pass
    return round(total_mem / (1024 * 1024), 1)

def get_active_window_pid():
    """Get PID of the foreground window"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return pid
    except:
        pass
    return None

class ProcessManager:
    @staticmethod
    def trim_group(proc_name):
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == proc_name:
                    trim_pid(proc.info['pid'])
        except: pass
        return ProcessManager.get_process_group_memory(proc_name)

    @staticmethod
    def get_process_group_memory(proc_name):
        return get_process_group_memory(proc_name)

    @staticmethod
    def toggle_group_state(proc_name, suspend_action):
        save_suspended_state(proc_name, suspend_action)
        success = False
        for p in psutil.process_iter(['pid', 'name']):
            if p.info['name'] == proc_name:
                try:
                    pid = p.info['pid']
                    handle = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
                    if handle:
                        try:
                            if suspend_action:
                                status = ntdll.NtSuspendProcess(handle)
                            else:
                                status = ntdll.NtResumeProcess(handle)
                            if status == 0:
                                success = True
                        finally:
                            kernel32.CloseHandle(handle)
                except Exception as e:
                    print(f"Error toggling process group state for {proc_name}: {e}")
        return success

    @staticmethod
    def get_visible_windows_info():
        visible_map = {}
        def enum_window_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                visible_map[pid] = True
        try: win32gui.EnumWindows(enum_window_callback, None)
        except: pass
        return visible_map
