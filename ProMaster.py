"""
ProMaster 12.4 — без переключателя темы (только тёмная).
"""

import os
import sys
import time
import ctypes
import threading
import subprocess
import glob
import hashlib
import math
import socket
import urllib.request
import winreg
from dataclasses import dataclass
from collections import defaultdict

import psutil
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import tkinter as tk
from send2trash import send2trash


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =========================================================
# ТЁМНАЯ ТЕМА
# =========================================================
THEME = {
    "BG": "#0a0a12", "BG_PANEL": "#101019", "BG_CARD": "#18182a",
    "BG_CARD_HI": "#21213a", "BG_INPUT": "#1f1f33",
    "TEXT": "#ffffff", "TEXT_SOFT": "#b8b8d0", "TEXT_DIM": "#6a6a88",
    "ACCENT": "#6366f1", "ACCENT_HI": "#818cf8",
    "CYAN": "#06b6d4", "PINK": "#ec4899", "GREEN": "#10b981",
    "AMBER": "#f59e0b", "PURPLE": "#a855f7", "RED": "#ef4444",
    "SIDEBAR_ACTIVE_BG": "#18182a",
    "SIDEBAR_ACTIVE_FG": "#ffffff",
    "SIDEBAR_ACTIVE_BORDER": "#18182a",
    "SIDEBAR_BORDER_W": 0,
}


# =========================================================
# СЛОВАРЬ КЛАССОВ УСТРОЙСТВ
# =========================================================
DEVICE_CLASSES_RU = {
    "Display": "Видеоадаптеры", "Monitor": "Мониторы",
    "Media": "Звуковые, видео и игровые устройства",
    "AudioEndpoint": "Звуковые устройства", "MEDIA": "Звуковые устройства",
    "Sound": "Звуковые устройства", "Net": "Сетевые адаптеры",
    "NET": "Сетевые адаптеры", "Network": "Сетевые адаптеры",
    "USB": "USB-устройства",
    "HIDClass": "Устройства HID",
    "Keyboard": "Клавиатуры",
    "Mouse": "Мыши и указывающие устройства",
    "System": "Системные устройства", "Processor": "Процессоры",
    "SCSIAdapter": "Контроллеры запоминающих устройств",
    "DiskDrive": "Дисковые устройства", "CDROM": "DVD и CD-ROM дисководы",
    "Volume": "Тома", "VolumeSnapshot": "Тома",
    "HDC": "Контроллеры IDE ATA/ATAPI", "Printer": "Принтеры",
    "PrintQueue": "Очереди печати", "Image": "Устройства обработки изображений",
    "Camera": "Камеры", "Bluetooth": "Bluetooth-устройства",
    "Modem": "Модемы", "Ports": "Порты (COM и LPT)",
    "Battery": "Батареи", "Firmware": "Встроенное ПО",
    "SecurityDevices": "Устройства безопасности",
    "SmartCardReader": "Устройства чтения смарт-карт",
    "SmartCard": "Смарт-карты", "SoftwareDevice": "Программные устройства",
    "SoftwareComponent": "Программные компоненты",
    "Sensor": "Датчики", "Biometric": "Биометрические устройства",
    "WPD": "Портативные устройства",
    "WindowsPortableDevice": "Портативные устройства",
    "PnpPrinters": "Принтеры PnP", "Other": "Другие устройства",
    "Unknown": "Неизвестные устройства",
}


def translate_class(cls_name):
    if not cls_name:
        return "Другие устройства"
    cls_clean = cls_name.strip()
    if cls_clean in DEVICE_CLASSES_RU:
        return DEVICE_CLASSES_RU[cls_clean]
    for key, val in DEVICE_CLASSES_RU.items():
        if key.lower() == cls_clean.lower():
            return val
    for key, val in DEVICE_CLASSES_RU.items():
        if key.lower() in cls_clean.lower():
            return val
    return cls_clean


# =========================================================
# ЛОГ
# =========================================================
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "masterlog.txt")


def write_log(entry):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {entry}\n")
    except Exception:
        pass


def read_log_tail(n=500):
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()[-n:]
    except Exception:
        return []


# =========================================================
# ПРАВА
# =========================================================
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = f'"{script}"'
    try:
        return ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1) > 32
    except Exception:
        return False


# =========================================================
# ПУТИ
# =========================================================
def system_drive():
    return os.environ.get("SystemDrive", "C:") + "\\"


def temp_paths():
    out = []
    for v in ("TEMP", "TMP"):
        p = os.environ.get(v)
        if p and os.path.isdir(p):
            out.append(p)
    w = os.path.join(system_drive(), "Windows", "Temp")
    if os.path.isdir(w):
        out.append(w)
    return out


def browser_paths():
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    result = []
    for base in [
        os.path.join(local, "Google", "Chrome", "User Data"),
        os.path.join(local, "Microsoft", "Edge", "User Data"),
        os.path.join(local, "Yandex", "YandexBrowser", "User Data"),
    ]:
        for prof in glob.glob(os.path.join(base, "*")):
            if os.path.isdir(prof):
                for s in ("Cache", "Code Cache", "GPUCache"):
                    p = os.path.join(prof, s)
                    if os.path.isdir(p):
                        result.append(p)
    for op in glob.glob(os.path.join(roaming, "Opera Software", "Opera*")):
        p = os.path.join(op, "Cache")
        if os.path.isdir(p):
            result.append(p)
    ff = os.path.join(local, "Mozilla", "Firefox", "Profiles")
    for prof in glob.glob(os.path.join(ff, "*")):
        if os.path.isdir(prof):
            p = os.path.join(prof, "cache2")
            if os.path.isdir(p):
                result.append(p)
    return result


def shader_cache_paths():
    local = os.environ.get("LOCALAPPDATA", "")
    result = []
    for p in [
        os.path.join(local, "NVIDIA", "DXCache"),
        os.path.join(local, "NVIDIA", "GLCache"),
        os.path.join(local, "NVIDIA Corporation", "NV_Cache"),
        os.path.join(local, "AMD", "DxCache"),
        os.path.join(local, "AMD", "DxcCache"),
        os.path.join(local, "AMD", "GLCache"),
        os.path.join(local, "D3DSCache"),
        os.path.join(local, "Intel", "ShaderCache"),
    ]:
        if os.path.isdir(p):
            result.append(p)
    return result


# =========================================================
# ДРАЙВЕРЫ
# =========================================================
def collect_drivers():
    devices = []
    used_method = "нет"

    try:
        import wmi
        c = wmi.WMI()
        for dev in c.Win32_PnPSignedDriver():
            try:
                name = dev.DeviceName or ""
                if not name:
                    continue
                cls_ru = translate_class(dev.DeviceClass or "Other")
                version = (dev.DriverVersion or "").strip()
                provider = (dev.DriverProviderName or "").strip()
                state = "ok" if version else "missing"
                if provider and "Microsoft" in provider and not version:
                    state = "ok"
                devices.append({
                    "name": name, "class": cls_ru,
                    "status": state, "version": version,
                    "provider": provider,
                })
            except Exception:
                continue
        if devices:
            used_method = "Win32_PnPSignedDriver"
    except Exception as e:
        write_log(f"PnPSignedDriver: {e}")

    if not devices:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-PnpDevice | Select-Object FriendlyName,Class,Status | "
                 "ConvertTo-Csv -NoTypeInformation"],
                capture_output=True, timeout=60)
            out = r.stdout.decode("utf-8", errors="ignore")
            for line in out.splitlines()[1:]:
                try:
                    parts = [p.strip('"') for p in line.split('","')]
                    if len(parts) < 3:
                        continue
                    name = parts[0].strip('"') or "Неизвестное устройство"
                    cls_ru = translate_class(parts[1].strip('"') or "Other")
                    status = parts[2].strip('"').lower()
                    state = "ok"
                    if "error" in status:
                        state = "error"
                    elif "unknown" in status:
                        state = "missing"
                    devices.append({
                        "name": name, "class": cls_ru,
                        "status": state, "version": "", "provider": "",
                    })
                except Exception:
                    continue
            if devices:
                used_method = "PowerShell"
        except Exception as e:
            write_log(f"Get-PnpDevice: {e}")

    if not devices:
        try:
            r = subprocess.run(
                ["wmic", "path", "Win32_PnPEntity", "get",
                 "Name,PNPClass,ConfigManagerErrorCode", "/format:csv"],
                capture_output=True, timeout=60)
            out = r.stdout.decode("cp866", errors="ignore")
            for line in out.splitlines()[1:]:
                if not line.strip():
                    continue
                parts = line.split(",")
                if len(parts) < 4:
                    continue
                try:
                    err = parts[1].strip()
                    name = parts[2].strip()
                    cls_ru = translate_class(parts[3].strip() or "Other")
                    if not name:
                        continue
                    state = "ok"
                    if err == "28":
                        state = "missing"
                    elif err and err != "0":
                        state = "error"
                    devices.append({
                        "name": name, "class": cls_ru,
                        "status": state, "version": "", "provider": "",
                    })
                except Exception:
                    continue
            if devices:
                used_method = "WMIC"
        except Exception as e:
            write_log(f"WMIC: {e}")

    order = {"missing": 0, "error": 1, "ok": 2}
    devices.sort(key=lambda d: (order.get(d["status"], 3), d["name"]))
    return devices, used_method


# =========================================================
# S.M.A.R.T.
# =========================================================
def collect_disks_health():
    result = []
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-PhysicalDisk | Select-Object FriendlyName,HealthStatus,"
             "OperationalStatus,MediaType,@{Name='SizeGB';"
             "Expression={[math]::Round($_.Size/1GB,1)}} | "
             "ConvertTo-Csv -NoTypeInformation"],
            capture_output=True, timeout=30)
        out = r.stdout.decode("utf-8", errors="ignore")
        for line in out.splitlines()[1:]:
            try:
                parts = [p.strip('"') for p in line.split('","')]
                if len(parts) < 5:
                    continue
                result.append({
                    "name": parts[0].strip('"'),
                    "health": parts[1].strip('"'),
                    "status": parts[2].strip('"'),
                    "media": parts[3].strip('"'),
                    "size_gb": parts[4].strip('"'),
                })
            except Exception:
                continue
    except Exception as e:
        write_log(f"Get-PhysicalDisk: {e}")
    return result


# =========================================================
# КОНФИГУРАЦИЯ ПК
# =========================================================
def collect_hardware():
    info = {
        "cpu": "Неизвестно", "cores": "", "freq": "N/A",
        "socket": "Неизвестно", "generation": "Неизвестно",
        "cache": "N/A", "tdp": "N/A",
        "ram": "", "ram_type": "N/A", "ram_freq": "N/A", "ram_slots": "N/A",
        "gpu": "Неизвестно", "vram": "N/A", "vram_bytes": 0,
        "board": "Неизвестно", "bios": "Неизвестно",
        "system": "Неизвестно", "os": "Windows", "os_version": "",
        "disks": [],
    }
    info["cores"] = (f"{psutil.cpu_count(logical=False)} физ / "
                     f"{psutil.cpu_count(logical=True)} лог")
    freq = psutil.cpu_freq()
    info["freq"] = f"{freq.current:.0f} MHz" if freq else "N/A"
    info["ram"] = f"{psutil.virtual_memory().total / (1024**3):.1f} GB"

    try:
        for p in psutil.disk_partitions():
            if not p.fstype or "cdrom" in p.opts.lower():
                continue
            try:
                d = psutil.disk_usage(p.mountpoint)
                info["disks"].append({
                    "device": p.device.rstrip("\\"),
                    "mount": p.mountpoint, "fstype": p.fstype,
                    "total_gb": d.total / (1024**3),
                    "used_gb": (d.total - d.free) / (1024**3),
                    "free_gb": d.free / (1024**3),
                    "percent": d.percent,
                })
            except Exception:
                pass
    except Exception:
        pass

    try:
        import wmi
        c = wmi.WMI()
        for pr in c.Win32_Processor():
            if pr.Name:
                info["cpu"] = pr.Name.strip()
                name = info["cpu"]
                if "Intel" in name:
                    for word in name.split():
                        if word.endswith(("th", "st", "nd", "rd")):
                            info["generation"] = word + " Gen (Intel)"
                            break
                    else:
                        info["generation"] = "Intel Core"
                elif "Ryzen" in name or "AMD" in name:
                    for p in name.split():
                        if p.isdigit() and len(p) == 4:
                            info["generation"] = f"AMD Ryzen {p[0]}000 Series"
                            break
                    else:
                        info["generation"] = "AMD Ryzen"
            if pr.SocketDesignation:
                info["socket"] = pr.SocketDesignation.strip()
            l2 = int(pr.L2CacheSize or 0) // 1024
            l3 = int(pr.L3CacheSize or 0) // 1024
            if l2 or l3:
                info["cache"] = f"L2: {l2} МБ / L3: {l3} МБ"
            if pr.MaxClockSpeed:
                if "U" in name or "T" in name:
                    info["tdp"] = "~15-35 Вт"
                elif "K" in name or "H" in name or "X" in name:
                    info["tdp"] = "~95-125 Вт"
                else:
                    info["tdp"] = "~65 Вт"
            break

        memory_modules = c.Win32_PhysicalMemory()
        if memory_modules:
            info["ram_slots"] = f"{len(memory_modules)} шт."
            smbios_types = {20: "DDR", 21: "DDR2", 24: "DDR3",
                            26: "DDR4", 34: "DDR5"}
            mtype = memory_modules[0].SMBIOSMemoryType
            if mtype and int(mtype) in smbios_types:
                info["ram_type"] = smbios_types[int(mtype)]
            speeds = [int(m.Speed or 0) for m in memory_modules]
            speeds = [s for s in speeds if s > 0]
            if speeds:
                info["ram_freq"] = f"{max(speeds)} MHz"

        for vc in c.Win32_VideoController():
            if vc.Name and "Microsoft" not in vc.Name:
                info["gpu"] = vc.Name.strip()
                if vc.AdapterRAM:
                    try:
                        vram_b = int(vc.AdapterRAM)
                        info["vram_bytes"] = vram_b
                        info["vram"] = f"{vram_b / (1024**3):.1f} GB"
                    except Exception:
                        pass
                break

        for bb in c.Win32_BaseBoard():
            parts = []
            if bb.Manufacturer:
                parts.append(bb.Manufacturer.strip())
            if bb.Product:
                parts.append(bb.Product.strip())
            if parts:
                info["board"] = " ".join(parts)
            break

        for b in c.Win32_BIOS():
            if b.SMBIOSBIOSVersion:
                info["bios"] = b.SMBIOSBIOSVersion.strip()
            break

        for cs in c.Win32_ComputerSystem():
            parts = []
            if cs.Manufacturer and "System" not in cs.Manufacturer:
                parts.append(cs.Manufacturer.strip())
            if cs.Model:
                parts.append(cs.Model.strip())
            if parts:
                info["system"] = " ".join(parts)
            break

        for os_info in c.Win32_OperatingSystem():
            if os_info.Caption:
                info["os"] = os_info.Caption.replace("Microsoft ", "").strip()
            if os_info.Version:
                info["os_version"] = f"Build {os_info.Version}"
            break
    except Exception:
        pass
    return info


# =========================================================
# БЕЗОПАСНОСТЬ
# =========================================================
class SecurityChecker:
    @staticmethod
    def check_firewall():
        try:
            r = subprocess.run(
                ["netsh", "advfirewall", "show", "allprofiles", "state"],
                capture_output=True, timeout=10)
            out = r.stdout.decode("cp866", errors="ignore").lower()
            off = out.count("off")
            if off > 0:
                return False, f"Брандмауэр выключен в {off} профиле(ях)"
            return True, "Брандмауэр включён во всех профилях"
        except Exception as e:
            return None, f"Ошибка: {e}"

    @staticmethod
    def check_defender():
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "(Get-MpComputerStatus).RealTimeProtectionEnabled"],
                capture_output=True, timeout=15)
            out = r.stdout.decode("utf-8", errors="ignore").strip().lower()
            if "true" in out:
                return True, "Защита в реальном времени включена"
            return False, "Защитник Windows отключён"
        except Exception as e:
            return None, f"Ошибка: {e}"

    @staticmethod
    def check_uac():
        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
            val, _ = winreg.QueryValueEx(k, "EnableLUA")
            winreg.CloseKey(k)
            return (True, "UAC включён") if val == 1 else (False, "UAC отключён")
        except Exception as e:
            return None, f"Ошибка: {e}"

    @staticmethod
    def check_smartscreen():
        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer")
            try:
                val, _ = winreg.QueryValueEx(k, "SmartScreenEnabled")
                winreg.CloseKey(k)
                if str(val).lower() in ("warn", "block", "1", "on"):
                    return True, "SmartScreen активен"
                return False, f"SmartScreen: {val}"
            except FileNotFoundError:
                winreg.CloseKey(k)
                return None, "SmartScreen не настроен"
        except Exception as e:
            return None, f"Ошибка: {e}"

    @staticmethod
    def enable_firewall():
        try:
            subprocess.run(
                ["netsh", "advfirewall", "set", "allprofiles", "state", "on"],
                capture_output=True, timeout=10)
            return True, "Брандмауэр включён"
        except Exception as e:
            return False, f"Ошибка: {e}"

    @staticmethod
    def enable_defender():
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "Set-MpPreference -DisableRealtimeMonitoring $false"],
                capture_output=True, timeout=15)
            return True, "Защитник включён"
        except Exception as e:
            return False, f"Ошибка: {e}"

    @staticmethod
    def enable_uac():
        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "EnableLUA", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k)
            return True, "UAC включён (нужна перезагрузка)"
        except Exception as e:
            return False, f"Ошибка: {e}"


# =========================================================
# ТЕСТ СКОРОСТИ
# =========================================================
class SpeedTest:
    @staticmethod
    def test_download(progress_cb, max_bytes=10_000_000):
        url = f"https://speed.cloudflare.com/__down?bytes={max_bytes}"
        try:
            start = time.time()
            total = 0
            req = urllib.request.Request(
                url, headers={"User-Agent": "ProMaster"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    elapsed = time.time() - start
                    speed = ((total * 8) / (elapsed * 1_000_000)
                             if elapsed else 0)
                    progress_cb(total / max_bytes, speed)
            elapsed = time.time() - start
            return True, (total * 8) / (elapsed * 1_000_000)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def test_upload(progress_cb, size=2_000_000):
        url = "https://speed.cloudflare.com/__up"
        try:
            data = os.urandom(size)
            start = time.time()

            class PR:
                def __init__(s, d, cb, sz):
                    s.data = d
                    s.cb = cb
                    s.size = sz
                    s.sent = 0
                    s.pos = 0

                def read(s, n=-1):
                    if s.pos >= len(s.data):
                        return b""
                    if n < 0 or n > len(s.data) - s.pos:
                        n = len(s.data) - s.pos
                    chunk = s.data[s.pos:s.pos + n]
                    s.pos += n
                    s.sent += len(chunk)
                    elapsed = time.time() - start
                    speed = ((s.sent * 8) / (elapsed * 1_000_000)
                             if elapsed else 0)
                    s.cb(s.sent / s.size, speed)
                    return chunk

            req = urllib.request.Request(
                url, data=PR(data, progress_cb, size), method="POST",
                headers={"User-Agent": "ProMaster",
                         "Content-Type": "application/octet-stream",
                         "Content-Length": str(size)})
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
            elapsed = time.time() - start
            return True, (size * 8) / (elapsed * 1_000_000)
        except Exception as e:
            return False, str(e)


# =========================================================
# РЕЖИМЫ + ТВИКИ
# =========================================================
class PowerMode:
    SCHEMES = {
        "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
    }

    @staticmethod
    def set_plan(key):
        guid = PowerMode.SCHEMES.get(key)
        if not guid:
            return False, "Неизвестная схема"
        try:
            r = subprocess.run(["powercfg", "/setactive", guid],
                               capture_output=True, timeout=10)
            if r.returncode == 0:
                return True, "Схема питания изменена"
            return False, r.stderr.decode("cp866", errors="ignore")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def high_performance():
        ok, msg = PowerMode.set_plan("high")
        if not ok:
            return False, f"Не удалось: {msg}"
        try:
            subprocess.run(
                ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"],
                capture_output=True, timeout=5)
            subprocess.run(
                ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PROCTHROTTLEMIN", "100"],
                capture_output=True, timeout=5)
            subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"],
                           capture_output=True, timeout=5)
        except Exception:
            pass
        return True, ("Режим высокой производительности включён:\n"
                      "• Схема: Высокая производительность\n"
                      "• Процессор: 100% без троттлинга")

    @staticmethod
    def boost_cpu():
        ok, msg = PowerMode.set_plan("high")
        if not ok:
            return False, f"Не удалось: {msg}"
        try:
            subprocess.run(
                ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"],
                capture_output=True, timeout=5)
            subprocess.run(
                ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PROCTHROTTLEMIN", "100"],
                capture_output=True, timeout=5)
            subprocess.run(
                ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PERFBOOSTMODE", "2"],
                capture_output=True, timeout=5)
        except Exception:
            pass
        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "NetworkThrottlingIndex", 0,
                              winreg.REG_DWORD, 0xffffffff)
            winreg.CloseKey(k)
        except Exception as e:
            write_log(f"NetworkThrottlingIndex: {e}")
        try:
            subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"],
                           capture_output=True, timeout=5)
        except Exception:
            pass
        return True, ("Разгон процессора включён:\n"
                      "• Схема: Высокая производительность\n"
                      "• Процессор: 100% без троттлинга\n"
                      "• Turbo Boost активен\n"
                      "• Сетевой троттлинг отключён")

    @staticmethod
    def boost_ram():
        actions = []
        try:
            total_gb = psutil.virtual_memory().total / (1024 ** 3)
            initial_mb = int(total_gb * 1024 * 1.0)
            max_mb = int(total_gb * 1024 * 2.0)
            subprocess.run(
                ["wmic", "computersystem", "set",
                 "AutomaticManagedPagefile=False"],
                capture_output=True, timeout=10)
            subprocess.run(
                ["wmic", "pagefileset", "where",
                 "Name='C:\\\\pagefile.sys'", "set",
                 f"InitialSize={initial_mb},MaximumSize={max_mb}"],
                capture_output=True, timeout=15)
            actions.append(f"• Файл подкачки: {initial_mb} / {max_mb} МБ")
        except Exception:
            actions.append("• Файл подкачки: настройка (требует админ)")

        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "LargeSystemCache", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k)
            actions.append("• LargeSystemCache: включён")
        except Exception:
            pass

        try:
            psapi = ctypes.WinDLL("psapi")
            k32 = ctypes.WinDLL("kernel32")
            for proc in psutil.process_iter(["pid"]):
                try:
                    h = k32.OpenProcess(0x0400 | 0x0100, False,
                                        proc.info["pid"])
                    if h:
                        psapi.EmptyWorkingSet(h)
                        k32.CloseHandle(h)
                except Exception:
                    pass
            actions.append("• Рабочие наборы памяти очищены")
        except Exception:
            pass

        return True, "Разгон оперативной памяти:\n" + "\n".join(actions)

    @staticmethod
    def boost_vram():
        actions = []
        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "HwSchMode", 0, winreg.REG_DWORD, 2)
            winreg.CloseKey(k)
            actions.append("• Аппаратное ускорение GPU (HAGS): включено")
        except Exception:
            pass
        try:
            subprocess.run(
                ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PCIEXPRESS", "ASPM", "0"],
                capture_output=True, timeout=5)
            subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"],
                           capture_output=True, timeout=5)
            actions.append("• Энергосбережение PCIe: отключено")
        except Exception:
            pass
        return True, "Разгон видеопамяти:\n" + "\n".join(actions)

    @staticmethod
    def revert_all():
        """Возвращает Windows к дефолтным значениям."""
        actions = []
        try:
            PowerMode.set_plan("balanced")
            actions.append("✅ Схема питания: Сбалансированная")
        except Exception as e:
            actions.append(f"⚠️ Схема питания: {e}")

        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "NetworkThrottlingIndex", 0,
                              winreg.REG_DWORD, 10)
            winreg.CloseKey(k)
            actions.append("✅ NetworkThrottlingIndex: 10")
        except Exception as e:
            actions.append(f"⚠️ NetworkThrottlingIndex: {e}")

        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "LargeSystemCache", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(k)
            actions.append("✅ LargeSystemCache: 0")
        except Exception as e:
            actions.append(f"⚠️ LargeSystemCache: {e}")

        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "HwSchMode", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k)
            actions.append("✅ HwSchMode: 1")
        except Exception as e:
            actions.append(f"⚠️ HwSchMode: {e}")

        try:
            subprocess.run(
                ["wmic", "computersystem", "set",
                 "AutomaticManagedPagefile=True"],
                capture_output=True, timeout=10)
            actions.append("✅ Файл подкачки: автоматически")
        except Exception as e:
            actions.append(f"⚠️ Файл подкачки: {e}")

        try:
            subprocess.run(
                ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PCIEXPRESS", "ASPM", "1"],
                capture_output=True, timeout=5)
            subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"],
                           capture_output=True, timeout=5)
            actions.append("✅ PCIe ASPM: стандарт")
        except Exception as e:
            actions.append(f"⚠️ PCIe ASPM: {e}")

        write_log("Откат всех твиков выполнен")
        return True, "Все твики отменены:\n" + "\n".join(actions)


def apply_traffic_saver(task):
    actions = []
    try:
        subprocess.run(["sc", "config", "wuauserv", "start=", "demand"],
                       capture_output=True, timeout=5)
        actions.append("• Автообновления Windows — вручную")
    except Exception:
        pass
    t = task.lower()
    if "браузер" in t:
        actions.append("• Включите экономию трафика в браузере")
    elif "игр" in t:
        actions.append("• Отключите фоновые загрузки в Steam/Epic")
    elif "видео" in t:
        actions.append("• Снизьте качество видео до 480p")
    else:
        actions.append("• Универсальный режим")
    return True, "Режим экономии трафика включён:\n" + "\n".join(actions)


def economy_energy():
    ok, msg = PowerMode.set_plan("saver")
    if not ok:
        return False, msg
    try:
        subprocess.run(
            ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
             "SUB_PROCESSOR", "PROCTHROTTLEMAX", "50"],
            capture_output=True, timeout=5)
        subprocess.run(
            ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
             "SUB_PROCESSOR", "PROCTHROTTLEMIN", "5"],
            capture_output=True, timeout=5)
        subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"],
                       capture_output=True, timeout=5)
    except Exception:
        pass
    return True, ("Режим экономии энергии включён:\n"
                  "• Схема: Экономия энергии\n"
                  "• Процессор: до 50%")


# =========================================================
# РЕЗУЛЬТАТ
# =========================================================
@dataclass
class ScanResult:
    files: int = 0
    bytes_: int = 0
    skipped: int = 0

    @property
    def mb(self):
        return self.bytes_ / (1024 * 1024)


# =========================================================
# ДВИЖОК ОЧИСТКИ
# =========================================================
class Engine:
    def _iter(self, paths):
        for base in paths:
            if not os.path.isdir(base):
                continue
            for root, dirs, files in os.walk(base, topdown=False):
                for n in files:
                    yield os.path.join(root, n)
                for n in dirs:
                    yield os.path.join(root, n)

    def scan(self, paths, on_progress, on_done):
        threading.Thread(target=self._scan_worker,
                         args=(paths, on_progress, on_done),
                         daemon=True).start()

    def _scan_worker(self, paths, on_progress, on_done):
        r = ScanResult()
        items = list(self._iter(paths))
        total = len(items) or 1
        for i, p in enumerate(items):
            try:
                if os.path.isfile(p):
                    r.files += 1
                    r.bytes_ += os.path.getsize(p)
            except (OSError, PermissionError):
                r.skipped += 1
            if i % 50 == 0:
                on_progress(int(i / total * 100))
        on_done(r)

    def clean(self, paths, on_progress, on_done, use_trash=False):
        threading.Thread(target=self._clean_worker,
                         args=(paths, on_progress, on_done, use_trash),
                         daemon=True).start()

    def _clean_worker(self, paths, on_progress, on_done, use_trash):
        r = ScanResult()
        items = list(self._iter(paths))
        total = len(items) or 1
        for i, p in enumerate(items):
            try:
                if os.path.isfile(p):
                    size = os.path.getsize(p)
                    if use_trash:
                        send2trash(p)
                    else:
                        os.remove(p)
                    r.files += 1
                    r.bytes_ += size
                elif os.path.isdir(p):
                    try:
                        os.rmdir(p)
                    except OSError:
                        pass
            except (OSError, PermissionError):
                r.skipped += 1
            if i % 50 == 0:
                on_progress(int(i / total * 100))
        on_done(r)


# =========================================================
# ПЛАВНАЯ ПРОКРУТКА
# =========================================================
def enable_smooth_scroll(widget):
    state = {"velocity": 0, "after_id": None}

    def apply_scroll():
        if abs(state["velocity"]) < 0.1:
            state["velocity"] = 0
            state["after_id"] = None
            return
        try:
            widget.yview_scroll(int(state["velocity"]), "units")
        except Exception:
            return
        state["velocity"] *= 0.85
        state["after_id"] = widget.after(16, apply_scroll)

    def on_wheel(event):
        delta = -1 if event.delta > 0 else 1
        state["velocity"] += delta * 2
        state["velocity"] = max(-12, min(12, state["velocity"]))
        if state["after_id"] is None:
            apply_scroll()

    def bind_recursive(w):
        try:
            w.bind("<MouseWheel>", on_wheel, add="+")
        except Exception:
            pass
        for child in w.winfo_children():
            bind_recursive(child)

    bind_recursive(widget)


# =========================================================
# КОЛЬЦО
# =========================================================
class Ring(ctk.CTkFrame):
    def __init__(self, parent, title, color_key, size=180):
        super().__init__(parent, fg_color="transparent")
        self.color_key = color_key
        self.size = size
        self.canvas = tk.Canvas(
            self, width=size, height=size,
            bg=THEME["BG_CARD"], highlightthickness=0)
        self.canvas.pack()
        self.title_lbl = ctk.CTkLabel(
            self, text=title, text_color=THEME["TEXT"],
            font=("Segoe UI", 15, "bold"))
        self.title_lbl.pack(pady=(10, 0))
        self._draw_ring(0)

    def _draw_ring(self, percent):
        color = THEME[self.color_key]
        self.canvas.delete("all")
        pad = 14
        s = self.size
        self.canvas.create_oval(pad, pad, s - pad, s - pad,
                                outline=THEME["BG_INPUT"], width=16)
        angle = int(360 * max(0, min(1, percent / 100)))
        if angle > 0:
            self.canvas.create_arc(pad, pad, s - pad, s - pad,
                                   start=90, extent=-angle,
                                   outline=color, width=16, style="arc")

    def set(self, percent, big_text=None, sub_text=None):
        self._draw_ring(percent)
        self.canvas.delete("text")
        s = self.size
        color = THEME[self.color_key]
        if big_text:
            self.canvas.create_text(s / 2, s / 2 - 10, text=big_text,
                                    fill=color,
                                    font=("Segoe UI", 32, "bold"),
                                    tags="text")
        if sub_text:
            self.canvas.create_text(s / 2, s / 2 + 26, text=sub_text,
                                    fill=THEME["TEXT_SOFT"],
                                    font=("Segoe UI", 13), tags="text")

    def apply_theme(self):
        self.canvas.configure(bg=THEME["BG_CARD"])
        self.title_lbl.configure(text_color=THEME["TEXT"])


# =========================================================
# КАРТОЧКА С ТЕСТОМ СКОРОСТИ
# =========================================================
class SpeedCard(ctk.CTkFrame):
    def __init__(self, parent, icon, title, color_key, mode):
        super().__init__(parent, corner_radius=14,
                         fg_color=THEME["BG_CARD"],
                         width=240, height=210)
        self.pack_propagate(False)
        self.color_key = color_key
        self.mode = mode
        self.testing = False

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=16)

        self.icon_lbl = ctk.CTkLabel(inner, text=icon,
                                     font=("Segoe UI Emoji", 26),
                                     text_color=THEME[color_key])
        self.icon_lbl.pack(pady=(0, 4))
        self.title_lbl = ctk.CTkLabel(inner, text=title,
                                      text_color=THEME["TEXT_DIM"],
                                      font=("Segoe UI", 11))
        self.title_lbl.pack()
        self.value = ctk.CTkLabel(inner, text="--",
                                  text_color=THEME["TEXT"],
                                  font=("Segoe UI", 20, "bold"))
        self.value.pack(pady=(6, 4))
        self.progress = ctk.CTkProgressBar(
            inner, height=8, corner_radius=4,
            progress_color=THEME[color_key])
        self.progress.pack(fill="x", pady=(2, 4))
        self.progress.set(0)
        self.test_btn = ctk.CTkButton(
            inner, text="Тест скорости", command=self.start_test,
            width=160, height=32, corner_radius=10,
            fg_color=THEME["ACCENT"], hover_color=THEME["ACCENT_HI"],
            font=("Segoe UI", 11, "bold"))
        self.test_btn.pack(pady=(4, 0))

    def start_test(self):
        if self.testing:
            return
        self.testing = True
        self.test_btn.configure(text="Тест…", state="disabled")
        self.progress.set(0)
        self.value.configure(text="0.0 Мбит/с")

        def on_progress(p, speed):
            def apply():
                try:
                    self.progress.set(p)
                    self.value.configure(text=f"{speed:.1f} Мбит/с")
                except Exception:
                    pass
            self.after(0, apply)

        def worker():
            if self.mode == "down":
                ok, result = SpeedTest.test_download(on_progress)
            else:
                ok, result = SpeedTest.test_upload(on_progress)

            def finish():
                self.testing = False
                self.test_btn.configure(text="Тест скорости", state="normal")
                self.progress.set(1)
                if ok:
                    self.value.configure(text=f"{result:.1f} Мбит/с")
                else:
                    self.value.configure(text="Ошибка")
            self.after(0, finish)
        threading.Thread(target=worker, daemon=True).start()

    def set(self, value):
        if not self.testing:
            self.value.configure(text=value)

    def apply_theme(self):
        self.configure(fg_color=THEME["BG_CARD"])
        self.icon_lbl.configure(text_color=THEME[self.color_key])
        self.title_lbl.configure(text_color=THEME["TEXT_DIM"])
        self.value.configure(text_color=THEME["TEXT"])
        self.progress.configure(progress_color=THEME[self.color_key])


# =========================================================
# ПРОСТАЯ КАРТОЧКА
# =========================================================
class StatCard(ctk.CTkFrame):
    def __init__(self, parent, icon, title, color_key):
        super().__init__(parent, corner_radius=14,
                         fg_color=THEME["BG_CARD"],
                         width=240, height=210)
        self.pack_propagate(False)
        self.color_key = color_key
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        self.icon_lbl = ctk.CTkLabel(inner, text=icon,
                                     font=("Segoe UI Emoji", 26),
                                     text_color=THEME[color_key])
        self.icon_lbl.pack(pady=(0, 4))
        self.title_lbl = ctk.CTkLabel(inner, text=title,
                                      text_color=THEME["TEXT_DIM"],
                                      font=("Segoe UI", 11))
        self.title_lbl.pack()
        self.value = ctk.CTkLabel(inner, text="--",
                                  text_color=THEME["TEXT"],
                                  font=("Segoe UI", 20, "bold"))
        self.value.pack(pady=(6, 0))

    def set(self, value):
        self.value.configure(text=value)

    def apply_theme(self):
        self.configure(fg_color=THEME["BG_CARD"])
        self.icon_lbl.configure(text_color=THEME[self.color_key])
        self.title_lbl.configure(text_color=THEME["TEXT_DIM"])
        self.value.configure(text_color=THEME["TEXT"])


# =========================================================
# ПЛИТКА С ПРОГРЕСС-БАРОМ
# =========================================================
class ActionTile(ctk.CTkFrame):
    def __init__(self, parent, icon, title, subtitle, color_key,
                 on_run, mode="cleanup"):
        super().__init__(parent, fg_color=THEME["BG_CARD"], corner_radius=14)
        self.color_key = color_key
        self.on_run = on_run
        self.mode = mode
        self.running = False

        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=18, pady=18)
        self.icon_lbl = ctk.CTkLabel(pad, text=icon,
                                     font=("Segoe UI Emoji", 40),
                                     text_color=THEME[color_key])
        self.icon_lbl.pack(anchor="w")
        self.title_lbl = ctk.CTkLabel(pad, text=title,
                                      text_color=THEME["TEXT"],
                                      font=("Segoe UI", 15, "bold"))
        self.title_lbl.pack(anchor="w", pady=(10, 0))
        self.sub_lbl = ctk.CTkLabel(pad, text=subtitle,
                                    text_color=THEME["TEXT_DIM"],
                                    font=("Segoe UI", 10))
        self.sub_lbl.pack(anchor="w")
        self.progress = ctk.CTkProgressBar(
            pad, height=6, corner_radius=3,
            progress_color=THEME[color_key])
        self.progress.pack(fill="x", pady=(10, 0))
        self.progress.set(0)
        self.result_lbl = ctk.CTkLabel(pad, text="",
                                       text_color=THEME["GREEN"],
                                       font=("Segoe UI", 11, "bold"))
        self.result_lbl.pack(anchor="w", pady=(6, 0))

        for w in (self, pad, self.icon_lbl, self.title_lbl, self.sub_lbl):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        self.progress_value = 0.0
        self.anim_id = None
        self.start_time = 0.0
        self.min_duration = 2.5
        self._work_done = False
        self._pending_result = None

    def _on_enter(self, e):
        if not self.running:
            self.configure(fg_color=THEME["BG_CARD_HI"])

    def _on_leave(self, e):
        if not self.running:
            self.configure(fg_color=THEME["BG_CARD"])

    def _on_click(self, e):
        if self.running:
            return
        self.running = True
        self.result_lbl.configure(text="")
        self.progress_value = 0.0
        self.progress.set(0)
        self.start_time = time.time()
        self._work_done = False
        self._pending_result = None
        self._animate_progress()

        def worker():
            try:
                result_text = self.on_run()
            except Exception as ex:
                result_text = f"Ошибка: {ex}"
            self._pending_result = result_text
            self._work_done = True
        threading.Thread(target=worker, daemon=True).start()

    def _animate_progress(self):
        if not self.running:
            return
        elapsed = time.time() - self.start_time
        target = min(0.95, elapsed / self.min_duration * 0.95)
        if self._work_done and elapsed >= self.min_duration:
            self.progress.set(1.0)
            self._finish(self._pending_result)
            return
        if self.progress_value < target:
            self.progress_value = min(target, self.progress_value + 0.02)
        self.progress.set(self.progress_value)
        self.anim_id = self.after(30, self._animate_progress)

    def _finish(self, result_text):
        self.running = False
        if self.anim_id:
            try:
                self.after_cancel(self.anim_id)
            except Exception:
                pass
            self.anim_id = None
        self.progress.set(1.0)
        if self.mode == "mode":
            self.icon_lbl.configure(text="✅", text_color=THEME["GREEN"])
            self.result_lbl.configure(text="Готово",
                                      text_color=THEME["GREEN"])
        else:
            self.result_lbl.configure(
                text=result_text or "Готово",
                text_color=THEME["GREEN"])
        self.after(2000, self._reset_progress)

    def _reset_progress(self):
        def step(i):
            if i > 20:
                self.progress.set(0)
                self.progress_value = 0.0
                return
            v = 1.0 - i / 20
            self.progress.set(max(0, v))
            self.after(30, lambda: step(i + 1))
        step(0)

    def apply_theme(self):
        self.configure(fg_color=THEME["BG_CARD"])
        self.icon_lbl.configure(text_color=THEME[self.color_key])
        self.title_lbl.configure(text_color=THEME["TEXT"])
        self.sub_lbl.configure(text_color=THEME["TEXT_DIM"])
        self.progress.configure(progress_color=THEME[self.color_key])


# =========================================================
# САЙДБАР
# =========================================================
class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_select):
        super().__init__(parent, fg_color=THEME["BG_PANEL"],
                         width=220, corner_radius=0)
        self.pack_propagate(False)
        self.on_select = on_select
        self.buttons = {}

        logo = ctk.CTkFrame(self, fg_color="transparent")
        logo.pack(fill="x", padx=20, pady=(24, 24))
        self.logo_pro = ctk.CTkLabel(logo, text="Pro",
                                     font=("Segoe UI", 22, "bold"),
                                     text_color=THEME["ACCENT_HI"])
        self.logo_pro.pack(side="left")
        self.logo_master = ctk.CTkLabel(logo, text="Master",
                                        font=("Segoe UI", 16),
                                        text_color=THEME["TEXT"])
        self.logo_master.pack(side="left", padx=(2, 0))

        items = [
            ("overview", "Обзор"), ("cleanup", "Очистка"),
            ("files", "Файлы"), ("drivers", "Драйверы"),
            ("smart", "S.M.A.R.T."), ("modes", "Режимы работы"),
            ("security", "Безопасность"), ("log", "Журнал"),
            ("settings", "Настройки"),
        ]
        for key, label in items:
            btn = ctk.CTkButton(
                self, text=f"  {label}", anchor="w", height=42,
                corner_radius=10, fg_color="transparent",
                hover_color=THEME["BG_CARD_HI"],
                text_color=THEME["TEXT_SOFT"],
                font=("Segoe UI", 13),
                command=lambda k=key: self.select(k))
            btn.pack(fill="x", padx=12, pady=2)
            self.buttons[key] = btn

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=18)
        ctk.CTkLabel(bottom, text="Режим работы",
                     text_color=THEME["TEXT_DIM"],
                     font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 6))
        adm = is_admin()
        self.priv_label = ctk.CTkLabel(
            bottom,
            text=("Администратор" if adm else "Пользователь"),
            text_color=(THEME["GREEN"] if adm else THEME["AMBER"]),
            font=("Segoe UI", 12, "bold"))
        self.priv_label.pack(anchor="w", pady=(0, 6))
        self.priv_switch = ctk.CTkSwitch(
            bottom, text="", command=self._toggle_admin,
            onvalue=True, offvalue=False,
            progress_color=THEME["GREEN"], fg_color=THEME["BG_INPUT"])
        self.priv_switch.pack(anchor="w")
        if adm:
            self.priv_switch.select()

    def select(self, key):
        for k, btn in self.buttons.items():
            if k == key:
                btn.configure(
                    fg_color=THEME["SIDEBAR_ACTIVE_BG"],
                    text_color=THEME["SIDEBAR_ACTIVE_FG"],
                    border_width=THEME["SIDEBAR_BORDER_W"],
                    border_color=THEME["SIDEBAR_ACTIVE_BORDER"])
            else:
                btn.configure(fg_color="transparent",
                              text_color=THEME["TEXT_SOFT"], border_width=0)
        self.on_select(key)

    def _toggle_admin(self):
        want = bool(self.priv_switch.get())
        if want and not is_admin():
            if restart_as_admin():
                self.winfo_toplevel().destroy()
            else:
                self.priv_switch.deselect()
        elif not want and is_admin():
            messagebox.showinfo("ProMaster",
                                "Понижение прав невозможно без перезапуска.")
            self.priv_switch.select()

    def apply_theme(self):
        self.configure(fg_color=THEME["BG_PANEL"])
        self.logo_pro.configure(text_color=THEME["ACCENT_HI"])
        self.logo_master.configure(text_color=THEME["TEXT"])
        for btn in self.buttons.values():
            btn.configure(hover_color=THEME["BG_CARD_HI"],
                          text_color=THEME["TEXT_SOFT"])
        self.priv_label.configure(
            text_color=(THEME["GREEN"] if is_admin() else THEME["AMBER"]))
        self.priv_switch.configure(progress_color=THEME["GREEN"],
                                   fg_color=THEME["BG_INPUT"])


# =========================================================
# АНИМАЦИЯ ПАПОК
# =========================================================
class SecurityAnimation:
    def __init__(self, canvas, get_color):
        self.canvas = canvas
        self.color = get_color
        self.running = False
        self.w = 400
        self.h = 240
        self.folder_w = 60
        self.folder_h = 50
        self.folder_y = self.h / 2 - self.folder_h / 2
        self.folders = [{"x": -80}, {"x": self.w / 2 - 30}, {"x": self.w + 40}]
        self.lens_angle = 0

    def start(self):
        self.running = True
        self._tick()

    def _tick(self):
        if not self.running:
            return
        self._draw()
        self.canvas.after(40, self._tick)

    def _draw_folder(self, x, y, w, h, color):
        tab_w = w * 0.4
        tab_h = h * 0.18
        self.canvas.create_polygon(
            x, y + tab_h, x + tab_w, y + tab_h,
            x + tab_w + 10, y, x, y,
            fill=color, outline="", tags="anim")
        self.canvas.create_rectangle(
            x, y + tab_h, x + w, y + h,
            fill=color, outline="", tags="anim")
        for i in range(3):
            ly = y + tab_h + 12 + i * 8
            self.canvas.create_line(x + 8, ly, x + w - 8, ly,
                                    fill="#ffffff", width=2, tags="anim")

    def _draw_lens(self, cx, cy, r):
        color = self.color("ACCENT")
        self.canvas.create_line(
            cx + r * 0.7, cy + r * 0.7, cx + r * 1.5, cy + r * 1.5,
            fill=color, width=6, capstyle="round", tags="anim")
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                outline=color, width=5, fill="", tags="anim")
        self.canvas.create_oval(
            cx - r * 0.5, cy - r * 0.5, cx - r * 0.1, cy - r * 0.1,
            fill="#ffffff", outline="", tags="anim")

    def _draw(self):
        self.canvas.delete("anim")
        color = self.color("ACCENT_HI")
        for f in self.folders:
            f["x"] -= 2.5
            if f["x"] < -100:
                f["x"] = self.w + 100
        for f in self.folders:
            center_x = self.w / 2 - self.folder_w / 2
            y_offset = -20 if abs(f["x"] - center_x) < 30 else 0
            self._draw_folder(f["x"], self.folder_y + y_offset,
                              self.folder_w, self.folder_h, color)
        cx = self.w / 2
        cy = self.h / 2 - 15
        self.lens_angle += 0.08
        ox = math.cos(self.lens_angle) * 15
        oy = math.sin(self.lens_angle) * 8
        self._draw_lens(cx + ox, cy + oy, 35)
        self.canvas.create_text(
            self.w / 2, self.h - 25,
            text="Проверяю файлы и настройки…",
            fill=self.color("TEXT_SOFT"),
            font=("Segoe UI", 12), tags="anim")


# =========================================================
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# =========================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ProMaster")
        self.geometry("1280x820")
        self.minsize(1150, 740)
        self.configure(fg_color=THEME["BG"])

        self.first = True
        self.use_trash = ctk.BooleanVar(value=False)
        self.pages = {}
        self.hw = collect_hardware()
        self.engine = Engine()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, on_select=self._switch_page)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.content = ctk.CTkFrame(self, fg_color=THEME["BG"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")

        self._build_overview()
        self._build_cleanup()
        self._build_files()
        self._build_drivers()
        self._build_smart()
        self._build_modes()
        self._build_security()
        self._build_log()
        self._build_settings()

        self.sidebar.select("overview")
        self.after(1000, self._refresh)

    def _switch_page(self, key):
        for name, page in self.pages.items():
            if name == key:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()

    # ---------- ОБЗОР ----------
    def _build_overview(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["overview"] = page

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 6))
        ctk.CTkLabel(head, text="Обзор системы",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(head, text="Обновление каждую секунду",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", pady=(2, 0))

        self.overview_bar = ctk.CTkProgressBar(
            page, height=4, corner_radius=2,
            progress_color=THEME["ACCENT"])
        self.overview_bar.pack(fill="x", padx=28, pady=(6, 18))
        self.overview_bar.set(0)
        self._start_overview_bar()

        ring_card = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"],
                                 corner_radius=16)
        ring_card.pack(fill="x", padx=28, pady=(0, 16))
        rings = ctk.CTkFrame(ring_card, fg_color="transparent")
        rings.pack(padx=24, pady=24, fill="x")

        self.ring_cpu = Ring(rings, "Процессор", "CYAN", size=180)
        self.ring_cpu.pack(side="left", expand=True)
        self.ring_ram = Ring(rings, "Оперативная память", "PURPLE", size=180)
        self.ring_ram.pack(side="left", expand=True)
        self.ring_disk = Ring(rings, "Накопитель", "PINK", size=180)
        self.ring_disk.pack(side="left", expand=True)
        self.ring_vram = Ring(rings, "Видеопамять", "GREEN", size=180)
        self.ring_vram.pack(side="left", expand=True)

        cards = ctk.CTkFrame(page, fg_color="transparent")
        cards.pack(fill="x", padx=28, pady=(0, 16))

        self.c_proc = StatCard(cards, "⚙️", "Процессов запущено", "GREEN")
        self.c_down = SpeedCard(cards, "⬇️", "Скачано из интернета",
                                "AMBER", mode="down")
        self.c_up = SpeedCard(cards, "⬆️", "Скорость отдачи",
                              "CYAN", mode="up")
        self.c_upt = StatCard(cards, "⏱", "Время работы ПК", "ACCENT_HI")

        for c in (self.c_proc, self.c_down, self.c_up, self.c_upt):
            c.pack(side="left", expand=True, fill="both", padx=6)

        disk_card = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"],
                                 corner_radius=16)
        disk_card.pack(fill="x", padx=28, pady=(0, 16))
        ctk.CTkLabel(disk_card, text="Накопители",
                     font=("Segoe UI", 13, "bold"),
                     text_color=THEME["TEXT_SOFT"]).pack(
            anchor="w", padx=22, pady=(14, 8))
        self.disk_rows = ctk.CTkFrame(disk_card, fg_color="transparent")
        self.disk_rows.pack(fill="x", padx=22, pady=(0, 16))

        info_card = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"],
                                 corner_radius=16, cursor="hand2")
        info_card.pack(fill="x", padx=28, pady=(0, 24))
        info_title = ctk.CTkLabel(
            info_card, text="Конфигурация компьютера  ›",
            font=("Segoe UI", 13, "bold"),
            text_color=THEME["TEXT_SOFT"])
        info_title.pack(anchor="w", padx=22, pady=(16, 8))
        info_preview = ctk.CTkLabel(
            info_card,
            text="Нажмите, чтобы посмотреть полную информацию о системе",
            font=("Segoe UI", 11), text_color=THEME["TEXT_DIM"])
        info_preview.pack(anchor="w", padx=22, pady=(0, 18))
        for w in (info_card, info_title, info_preview):
            w.bind("<Button-1>", lambda e: self._show_config_dialog())

    def _start_overview_bar(self):
        steps = 30

        def step(i):
            if i > steps:
                self.after(500, self._fade_overview_bar)
                return
            self.overview_bar.set(i / steps)
            self.after(30, lambda: step(i + 1))
        step(0)

    def _fade_overview_bar(self):
        def step(i):
            if i > 20:
                self.overview_bar.set(0)
                return
            self.overview_bar.set(1.0 - i / 20)
            self.after(30, lambda: step(i + 1))
        step(0)

    def _show_config_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Конфигурация компьютера")
        dlg.geometry("720x680")
        dlg.configure(fg_color=THEME["BG"])
        dlg.transient(self)
        dlg.grab_set()

        header = ctk.CTkFrame(dlg, fg_color=THEME["BG_CARD"], corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="Конфигурация компьютера",
                     font=("Segoe UI", 20, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w", padx=24,
                                                    pady=(20, 4))
        ctk.CTkLabel(header, text="Полная информация о системе",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", padx=24,
                                                        pady=(0, 16))
        scroll = ctk.CTkScrollableFrame(dlg, fg_color=THEME["BG"],
                                        corner_radius=0)
        scroll.pack(fill="both", expand=True)
        enable_smooth_scroll(scroll)

        grid_card = ctk.CTkFrame(scroll, fg_color=THEME["BG_CARD"],
                                 corner_radius=14)
        grid_card.pack(fill="x", padx=20, pady=(20, 12))
        ctk.CTkLabel(grid_card, text="Система",
                     font=("Segoe UI", 14, "bold"),
                     text_color=THEME["ACCENT_HI"]).pack(anchor="w", padx=20,
                                                          pady=(16, 8))
        grid = ctk.CTkFrame(grid_card, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=(0, 16))
        items = [
            ("Процессор", self.hw["cpu"]),
            ("Поколение", self.hw["generation"]),
            ("Ядра / потоки", self.hw["cores"]),
            ("Частота", self.hw["freq"]),
            ("Сокет", self.hw["socket"]),
            ("Кэш", self.hw["cache"]),
            ("Энергопотребление", self.hw["tdp"]),
            ("Оперативная память", self.hw["ram"]),
            ("Тип памяти", self.hw["ram_type"]),
            ("Частота памяти", self.hw["ram_freq"]),
            ("Модулей памяти", self.hw["ram_slots"]),
            ("Видеокарта", self.hw["gpu"]),
            ("Видеопамять", self.hw["vram"]),
            ("Материнская плата", self.hw["board"]),
            ("BIOS", self.hw["bios"]),
            ("Модель системы", self.hw["system"]),
            ("Операционная", self.hw["os"]),
            ("Версия системы", self.hw["os_version"]),
        ]
        for i, (lbl, val) in enumerate(items):
            r, c = i // 2, (i % 2) * 2
            ctk.CTkLabel(grid, text=lbl, text_color=THEME["TEXT_DIM"],
                         font=("Segoe UI", 11)).grid(
                row=r, column=c, sticky="w", padx=(0, 8), pady=6)
            ctk.CTkLabel(grid, text=val, text_color=THEME["TEXT"],
                         font=("Segoe UI", 12)).grid(
                row=r, column=c + 1, sticky="w", padx=(0, 30), pady=6)
        ctk.CTkButton(dlg, text="Закрыть", command=dlg.destroy,
                      width=140, height=38, corner_radius=10,
                      fg_color=THEME["ACCENT"],
                      hover_color=THEME["ACCENT_HI"]).pack(pady=16)

    # ---------- ОЧИСТКА ----------
    def _build_cleanup(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["cleanup"] = page

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 18))
        ctk.CTkLabel(head, text="Очистка системы",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(head, text="Нажмите на плитку для выполнения",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", pady=(2, 0))

        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.pack(fill="x", padx=28, pady=(0, 16))

        tiles = [
            ("🔍", "Анализ временных", "Показать объём", "CYAN",
             lambda: self._run_scan_temp()),
            ("🗑", "Очистить временные", "Удалить мусор", "CYAN",
             lambda: self._run_clean_temp()),
            ("🔎", "Анализ браузеров", "Размер кэша", "PURPLE",
             lambda: self._run_scan_browsers()),
            ("🌐", "Очистить кэш", "Без закладок", "PURPLE",
             lambda: self._run_clean_browsers()),
            ("🎮", "Игровой кэш шейдеров", "NVIDIA / AMD / DirectX", "PINK",
             lambda: self._run_shader_cache()),
            ("♻️", "Корзина", "Удалить навсегда", "PINK",
             lambda: self._run_clean_recycle()),
            ("⚡", "Освободить память", "Очистка RAM", "GREEN",
             lambda: self._run_clean_ram()),
        ]
        self.cleanup_tiles = []
        for i, (icon, title, subtitle, ckey, cmd) in enumerate(tiles):
            tile = ActionTile(grid, icon, title, subtitle, ckey, cmd)
            tile.grid(row=i // 3, column=i % 3,
                      padx=6, pady=6, sticky="nsew")
            grid.grid_columnconfigure(i % 3, weight=1)
            self.cleanup_tiles.append(tile)

        opts = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"], corner_radius=12)
        opts.pack(fill="x", padx=28, pady=(0, 16))
        ctk.CTkCheckBox(opts, text="Удалять в корзину (можно восстановить)",
                        variable=self.use_trash, font=("Segoe UI", 12),
                        fg_color=THEME["ACCENT"],
                        hover_color=THEME["ACCENT_HI"]
                        ).pack(anchor="w", padx=20, pady=14)

    def _run_scan_temp(self):
        holder = {"result": None, "done": False}
        def on_done(r):
            holder["result"] = f"Объём: {r.mb:.1f} МБ • файлов: {r.files}"
            holder["done"] = True
        self.engine.scan(temp_paths(), lambda p: None, on_done)
        while not holder["done"]:
            time.sleep(0.05)
        return holder["result"]

    def _run_clean_temp(self):
        holder = {"result": None, "done": False}
        def on_done(r):
            holder["result"] = f"Удалено: {r.files} • освобождено: {r.mb:.1f} МБ"
            holder["done"] = True
        self.engine.clean(temp_paths(), lambda p: None, on_done,
                          use_trash=self.use_trash.get())
        while not holder["done"]:
            time.sleep(0.05)
        return holder["result"]

    def _run_scan_browsers(self):
        holder = {"result": None, "done": False}
        def on_done(r):
            holder["result"] = f"Размер кэша: {r.mb:.1f} МБ • файлов: {r.files}"
            holder["done"] = True
        self.engine.scan(browser_paths(), lambda p: None, on_done)
        while not holder["done"]:
            time.sleep(0.05)
        return holder["result"]

    def _run_clean_browsers(self):
        holder = {"result": None, "done": False}
        def on_done(r):
            holder["result"] = f"Удалено: {r.files} • освобождено: {r.mb:.1f} МБ"
            holder["done"] = True
        self.engine.clean(browser_paths(), lambda p: None, on_done,
                          use_trash=self.use_trash.get())
        while not holder["done"]:
            time.sleep(0.05)
        return holder["result"]

    def _run_shader_cache(self):
        paths = shader_cache_paths()
        if not paths:
            return "Игровой кэш не найден"
        holder = {"result": None, "done": False}
        def on_done(r):
            holder["result"] = (f"Удалено: {r.files} файлов • "
                                f"освобождено: {r.mb:.1f} МБ")
            holder["done"] = True
        self.engine.clean(paths, lambda p: None, on_done,
                          use_trash=self.use_trash.get())
        while not holder["done"]:
            time.sleep(0.05)
        return holder["result"]

    def _run_clean_recycle(self):
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=30)
            return "Корзина очищена"
        except Exception as e:
            return f"Ошибка: {e}"

    def _run_clean_ram(self):
        try:
            psapi = ctypes.WinDLL("psapi")
            k32 = ctypes.WinDLL("kernel32")
            n = 0
            for proc in psutil.process_iter(["pid"]):
                try:
                    h = k32.OpenProcess(0x0400 | 0x0100, False,
                                        proc.info["pid"])
                    if h:
                        psapi.EmptyWorkingSet(h)
                        k32.CloseHandle(h)
                        n += 1
                except Exception:
                    pass
            return f"Обработано процессов: {n}"
        except Exception as e:
            return f"Ошибка: {e}"

    # ---------- ФАЙЛЫ (гибридный MD5) ----------
    def _build_files(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["files"] = page

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 18))
        ctk.CTkLabel(head, text="Поиск файлов",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(head, text="Дубликаты и большие файлы",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", pady=(2, 0))

        ctrl = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"], corner_radius=14)
        ctrl.pack(fill="x", padx=28, pady=(0, 12))

        row1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(row1, text="Папка для поиска:",
                     text_color=THEME["TEXT_SOFT"],
                     font=("Segoe UI", 13)).pack(side="left")
        self.search_path = ctk.StringVar(value=os.path.expanduser("~"))
        ctk.CTkEntry(row1, textvariable=self.search_path,
                     width=500, height=40, font=("Segoe UI", 13),
                     fg_color=THEME["BG_INPUT"], border_width=0
                     ).pack(side="left", padx=(10, 8))
        ctk.CTkButton(row1, text="Выбрать…", width=110, height=40,
                      font=("Segoe UI", 13),
                      fg_color=THEME["BG_INPUT"],
                      hover_color=THEME["BG_CARD_HI"],
                      command=self._choose_search_path).pack(side="left")

        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=20, pady=(6, 6))
        self.min_size_mb = ctk.IntVar(value=100)
        ctk.CTkLabel(row2, text="Мин. размер, МБ:",
                     text_color=THEME["TEXT_SOFT"],
                     font=("Segoe UI", 13)).pack(side="left")
        ctk.CTkEntry(row2, textvariable=self.min_size_mb,
                     width=100, height=40, font=("Segoe UI", 13),
                     fg_color=THEME["BG_INPUT"], border_width=0
                     ).pack(side="left", padx=(8, 20))
        ctk.CTkButton(row2, text="Найти дубликаты",
                      command=self._find_duplicates,
                      fg_color=THEME["PURPLE"],
                      hover_color=THEME["ACCENT_HI"],
                      font=("Segoe UI", 13),
                      width=180, height=42, corner_radius=10).pack(
            side="left", padx=6)
        ctk.CTkButton(row2, text="Найти большие файлы",
                      command=self._find_large,
                      fg_color=THEME["CYAN"],
                      hover_color=THEME["ACCENT_HI"],
                      font=("Segoe UI", 13),
                      width=190, height=42, corner_radius=10).pack(
            side="left", padx=6)
        ctk.CTkButton(row2, text="Удалить выбранные",
                      command=self._delete_checked,
                      fg_color=THEME["RED"], hover_color="#dc2626",
                      font=("Segoe UI", 13),
                      width=180, height=42, corner_radius=10).pack(
            side="left", padx=6)

        self.files_bar = ctk.CTkProgressBar(
            ctrl, height=6, corner_radius=3,
            progress_color=THEME["ACCENT"])
        self.files_bar.pack(fill="x", padx=20, pady=(4, 16))
        self.files_bar.set(0)

        table_card = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"],
                                  corner_radius=14)
        table_card.pack(fill="both", expand=True, padx=28, pady=(0, 12))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", background=THEME["BG_CARD"],
                        foreground=THEME["TEXT"],
                        fieldbackground=THEME["BG_CARD"],
                        borderwidth=0, rowheight=42,
                        font=("Segoe UI", 16))
        style.map("Treeview",
                  background=[("selected", THEME["ACCENT"]),
                              ("active", THEME["BG_CARD_HI"])],
                  foreground=[("selected", "#ffffff")])
        style.configure("Treeview.Heading", background=THEME["BG_INPUT"],
                        foreground=THEME["TEXT"],
                        font=("Segoe UI", 16, "bold"))

        cols = ("check", "path", "size")
        self.tree = ttk.Treeview(table_card, columns=cols,
                                 show="headings", height=10)
        self.tree.heading("check", text="✔")
        self.tree.heading("path", text="Путь")
        self.tree.heading("size", text="Размер")
        self.tree.column("check", width=70, anchor="center")
        self.tree.column("path", width=900, anchor="w")
        self.tree.column("size", width=180, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=14, pady=14)
        self.tree.bind("<Button-1>", self._toggle_check)
        self.tree.bind("<Motion>", self._on_tree_hover)

        def on_wheel(e):
            self.tree.yview_scroll(int(-1 * (e.delta / 120)) * 2, "units")
        self.tree.bind("<MouseWheel>", on_wheel, add="+")

        self._hovered_row = None
        self.checked_items = set()

        status_row = ctk.CTkFrame(page, fg_color="transparent")
        status_row.pack(fill="x", padx=28, pady=(0, 20))
        self.files_status = ctk.CTkLabel(status_row, text="Готово",
                                         font=("Segoe UI", 14),
                                         text_color=THEME["TEXT_DIM"])
        self.files_status.pack(anchor="w")

        self._files_anim_active = False

    def _animate_files_bar(self):
        if not self._files_anim_active:
            return
        self._files_bar_val = getattr(self, "_files_bar_val", 0.0) + 0.02
        if self._files_bar_val >= 1.0:
            self._files_bar_val = 1.0
        self.files_bar.set(self._files_bar_val)
        if self._files_bar_val < 1.0:
            self.after(30, self._animate_files_bar)

    def _start_files_bar(self):
        self._files_bar_val = 0.0
        self._files_anim_active = True
        self.files_bar.set(0)
        self._animate_files_bar()
        self.after(2500, self._stop_files_bar)

    def _stop_files_bar(self):
        self._files_anim_active = False
        self.files_bar.set(1.0)
        self.after(2000, self._reset_files_bar)

    def _reset_files_bar(self):
        def step(i):
            if i > 20:
                self.files_bar.set(0)
                self._files_bar_val = 0.0
                return
            self.files_bar.set(max(0, 1.0 - i / 20))
            self.after(30, lambda: step(i + 1))
        step(0)

    def _on_tree_hover(self, event):
        row = self.tree.identify_row(event.y)
        if row == self._hovered_row:
            return
        self._hovered_row = row
        for item in self.tree.get_children():
            self.tree.item(item, tags=())
        if row:
            self.tree.item(row, tags=("hover",))
            self.tree.tag_configure("hover",
                                    background=THEME["BG_CARD_HI"])

    def _choose_search_path(self):
        p = filedialog.askdirectory(initialdir=self.search_path.get())
        if p:
            self.search_path.set(p)

    def _toggle_check(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if item in self.checked_items:
            self.checked_items.discard(item)
            vals = self.tree.item(item, "values")
            self.tree.item(item, values=("☐", vals[1], vals[2]))
        else:
            self.checked_items.add(item)
            vals = self.tree.item(item, "values")
            self.tree.item(item, values=("☑", vals[1], vals[2]))

    def _fmt_size(self, sz):
        for u, n in [("ГБ", 1024 ** 3), ("МБ", 1024 ** 2), ("КБ", 1024)]:
            if sz >= n:
                return f"{sz / n:.1f} {u}"
        return f"{sz} Б"

    def _quick_hash(self, fp, chunk=65536):
        try:
            h = hashlib.md5()
            with open(fp, "rb") as f:
                h.update(f.read(chunk))
            return h.hexdigest()
        except Exception:
            return None

    def _full_hash(self, fp):
        try:
            h = hashlib.md5()
            with open(fp, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def _fill_tree(self, items, fmt, status_text):
        for fp, sz in items:
            self.tree.insert("", "end", values=("☐", fp, fmt(sz)))
        self.files_status.configure(text=status_text)

    def _find_duplicates(self):
        path = self.search_path.get()
        if not os.path.isdir(path):
            messagebox.showerror("ProMaster", "Папка не найдена")
            return
        self._start_files_bar()
        self.files_status.configure(text="Сканирую дубликаты…")
        self.tree.delete(*self.tree.get_children())
        self.checked_items.clear()
        threading.Thread(target=self._scan_duplicates,
                         args=(path,), daemon=True).start()

    def _scan_duplicates(self, path):
        sizes = defaultdict(list)
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    sz = os.path.getsize(fp)
                    if sz > 1024:
                        sizes[sz].append(fp)
                except (OSError, PermissionError):
                    continue

        candidates = []
        for sz, files in sizes.items():
            if len(files) > 1:
                candidates.extend(files)

        if not candidates:
            self.after(0, lambda: self._fill_tree(
                [], self._fmt_size, "Дубликатов не найдено"))
            return

        quick_groups = defaultdict(list)
        for fp in candidates:
            h = self._quick_hash(fp)
            if h:
                quick_groups[h].append(fp)

        final_groups = defaultdict(list)
        for h, files in quick_groups.items():
            if len(files) > 1:
                for fp in files:
                    full_h = self._full_hash(fp)
                    if full_h:
                        final_groups[full_h].append(fp)

        dups = []
        for h, files in final_groups.items():
            if len(files) > 1:
                for fp in files[1:]:
                    try:
                        sz = os.path.getsize(fp)
                    except Exception:
                        sz = 0
                    dups.append((fp, sz))

        dups.sort(key=lambda x: -x[1])
        self.after(0, lambda: self._fill_tree(
            dups, self._fmt_size,
            f"Найдено дубликатов: {len(dups)}"))

    def _find_large(self):
        path = self.search_path.get()
        if not os.path.isdir(path):
            messagebox.showerror("ProMaster", "Папка не найдена")
            return
        self._start_files_bar()
        self.files_status.configure(text="Сканирую большие файлы…")
        self.tree.delete(*self.tree.get_children())
        self.checked_items.clear()
        min_mb = int(self.min_size_mb.get() or 100)
        threading.Thread(target=self._scan_large,
                         args=(path, min_mb), daemon=True).start()

    def _scan_large(self, path, min_mb):
        big = []
        min_b = min_mb * 1024 * 1024
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    sz = os.path.getsize(fp)
                    if sz >= min_b:
                        big.append((fp, sz))
                except (OSError, PermissionError):
                    continue
        big.sort(key=lambda x: -x[1])
        self.after(0, lambda: self._fill_tree(
            big, self._fmt_size, f"Найдено больших файлов: {len(big)}"))

    def _delete_checked(self):
        if not self.checked_items:
            messagebox.showinfo("ProMaster", "Ничего не выбрано")
            return
        n = len(self.checked_items)
        if not messagebox.askyesno("ProMaster", f"Удалить {n} файлов?"):
            return
        ok = 0
        for item in list(self.checked_items):
            vals = self.tree.item(item, "values")
            fp = vals[1]
            try:
                if self.use_trash.get():
                    send2trash(fp)
                else:
                    os.remove(fp)
                ok += 1
                self.tree.delete(item)
            except Exception:
                pass
        self.checked_items.clear()
        messagebox.showinfo("ProMaster", f"Удалено файлов: {ok}")
        self.files_status.configure(text=f"Удалено: {ok}")

    # ---------- ДРАЙВЕРЫ ----------
    def _build_drivers(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["drivers"] = page

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 18))
        ctk.CTkLabel(head, text="Диспетчер устройств",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(head, text="Проверка установленных и отсутствующих драйверов",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", pady=(2, 0))

        btn_row = ctk.CTkFrame(page, fg_color="transparent")
        btn_row.pack(fill="x", padx=28, pady=(0, 12))
        ctk.CTkButton(btn_row, text="🔍  Обновить список",
                      command=self._refresh_drivers,
                      width=200, height=42, corner_radius=10,
                      fg_color=THEME["ACCENT"],
                      hover_color=THEME["ACCENT_HI"],
                      font=("Segoe UI", 13, "bold")).pack(side="left")
        self.drivers_status = ctk.CTkLabel(
            btn_row, text="Нажмите «Обновить список»",
            font=("Segoe UI", 12), text_color=THEME["TEXT_DIM"])
        self.drivers_status.pack(side="left", padx=16)

        self.drivers_bar = ctk.CTkProgressBar(
            page, height=6, corner_radius=3,
            progress_color=THEME["ACCENT"])
        self.drivers_bar.pack(fill="x", padx=28, pady=(0, 12))
        self.drivers_bar.set(0)

        self.drivers_scroll = ctk.CTkScrollableFrame(
            page, fg_color=THEME["BG_CARD"], corner_radius=14)
        self.drivers_scroll.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        enable_smooth_scroll(self.drivers_scroll)
        ctk.CTkLabel(self.drivers_scroll,
                     text="Нажмите «Обновить список» чтобы увидеть устройства",
                     font=("Segoe UI", 14),
                     text_color=THEME["TEXT_DIM"]).pack(pady=40)

    def _refresh_drivers(self):
        self.drivers_status.configure(text="Сканирую устройства…",
                                      text_color=THEME["TEXT_DIM"])
        for w in self.drivers_scroll.winfo_children():
            w.destroy()
        self._drivers_bar_val = 0.0
        self._drivers_anim_active = True
        self._animate_drivers_bar()
        self.after(2500, self._stop_drivers_bar)
        threading.Thread(target=self._drivers_worker, daemon=True).start()

    def _animate_drivers_bar(self):
        if not getattr(self, "_drivers_anim_active", False):
            return
        self._drivers_bar_val += 0.02
        if self._drivers_bar_val >= 1.0:
            self._drivers_bar_val = 1.0
        self.drivers_bar.set(self._drivers_bar_val)
        if self._drivers_bar_val < 1.0:
            self.after(30, self._animate_drivers_bar)

    def _stop_drivers_bar(self):
        self._drivers_anim_active = False
        self.drivers_bar.set(1.0)
        self.after(2000, lambda: self.drivers_bar.set(0))

    def _drivers_worker(self):
        try:
            devices, method = collect_drivers()
        except Exception as e:
            devices = []
            method = f"Ошибка: {e}"
        self.after(0, lambda: self._show_drivers(devices, method))

    def _show_drivers(self, devices, method):
        for w in self.drivers_scroll.winfo_children():
            w.destroy()
        if not devices:
            ctk.CTkLabel(self.drivers_scroll,
                         text=(f"Устройства не найдены.\n\n"
                               f"Метод: {method}\n"
                               f"Права администратора: "
                               f"{'ДА' if is_admin() else 'НЕТ'}"),
                         font=("Segoe UI", 13),
                         text_color=THEME["TEXT_DIM"],
                         justify="left").pack(pady=40, padx=20)
            self.drivers_status.configure(
                text=f"Не удалось получить список ({method})",
                text_color=THEME["AMBER"])
            return
        ok_c = sum(1 for d in devices if d["status"] == "ok")
        miss = sum(1 for d in devices if d["status"] == "missing")
        err = sum(1 for d in devices if d["status"] == "error")
        self.drivers_status.configure(
            text=(f"Всего: {len(devices)} • ✅ {ok_c} • ❌ {miss + err}  [{method}]"),
            text_color=THEME["TEXT_SOFT"])
        groups = defaultdict(list)
        for d in devices:
            groups[d["class"]].append(d)
        for cls_name in sorted(groups.keys()):
            cls_devs = groups[cls_name]
            head = ctk.CTkFrame(self.drivers_scroll, fg_color="transparent")
            head.pack(fill="x", padx=10, pady=(10, 4))
            ctk.CTkLabel(head, text=f"📂  {cls_name}",
                         font=("Segoe UI", 14, "bold"),
                         text_color=THEME["ACCENT_HI"]).pack(side="left")
            ctk.CTkLabel(head, text=f"({len(cls_devs)})",
                         font=("Segoe UI", 12),
                         text_color=THEME["TEXT_DIM"]).pack(side="left", padx=8)
            for d in cls_devs:
                row = ctk.CTkFrame(self.drivers_scroll,
                                   fg_color=THEME["BG_CARD_HI"],
                                   corner_radius=8)
                row.pack(fill="x", padx=6, pady=2)
                icon = {"ok": "✅", "missing": "❌",
                        "error": "⚠️"}.get(d["status"], "❓")
                ck = {"ok": "GREEN", "missing": "RED",
                      "error": "AMBER"}.get(d["status"], "TEXT")
                ctk.CTkLabel(row, text=icon,
                             font=("Segoe UI Emoji", 18),
                             text_color=THEME[ck]).pack(side="left",
                                                        padx=(12, 8), pady=8)
                txt = ctk.CTkFrame(row, fg_color="transparent")
                txt.pack(side="left", fill="x", expand=True, pady=6)
                ctk.CTkLabel(txt, text=d["name"],
                             font=("Segoe UI", 13, "bold"),
                             text_color=THEME["TEXT"],
                             anchor="w").pack(anchor="w")
                sub = ""
                if d["version"]:
                    sub = f"Версия драйвера: {d['version']}"
                elif d["provider"]:
                    sub = f"Поставщик: {d['provider']}"
                if sub:
                    ctk.CTkLabel(txt, text=sub, font=("Segoe UI", 10),
                                 text_color=THEME["TEXT_DIM"],
                                 anchor="w").pack(anchor="w")
        write_log(f"Драйверы: {len(devices)} устройств через {method}")

    # ---------- S.M.A.R.T. ----------
    def _build_smart(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["smart"] = page

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 18))
        ctk.CTkLabel(head, text="Здоровье накопителей (S.M.A.R.T.)",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(head, text="Проверка состояния SSD и HDD",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", pady=(2, 0))

        btn_row = ctk.CTkFrame(page, fg_color="transparent")
        btn_row.pack(fill="x", padx=28, pady=(0, 12))
        ctk.CTkButton(btn_row, text="🔍  Проверить диски",
                      command=self._refresh_smart,
                      width=200, height=42, corner_radius=10,
                      fg_color=THEME["ACCENT"],
                      hover_color=THEME["ACCENT_HI"],
                      font=("Segoe UI", 13, "bold")).pack(side="left")
        self.smart_status = ctk.CTkLabel(
            btn_row, text="Нажмите «Проверить диски»",
            font=("Segoe UI", 12), text_color=THEME["TEXT_DIM"])
        self.smart_status.pack(side="left", padx=16)

        self.smart_bar = ctk.CTkProgressBar(
            page, height=6, corner_radius=3,
            progress_color=THEME["ACCENT"])
        self.smart_bar.pack(fill="x", padx=28, pady=(0, 12))
        self.smart_bar.set(0)

        self.smart_scroll = ctk.CTkScrollableFrame(
            page, fg_color=THEME["BG_CARD"], corner_radius=14)
        self.smart_scroll.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        enable_smooth_scroll(self.smart_scroll)
        ctk.CTkLabel(self.smart_scroll,
                     text="Нажмите кнопку, чтобы проверить состояние дисков",
                     font=("Segoe UI", 14),
                     text_color=THEME["TEXT_DIM"]).pack(pady=40)

    def _refresh_smart(self):
        self.smart_status.configure(text="Проверяю диски…",
                                    text_color=THEME["TEXT_DIM"])
        for w in self.smart_scroll.winfo_children():
            w.destroy()
        self._smart_bar_val = 0.0
        self._smart_anim_active = True
        self._animate_smart_bar()
        self.after(2000, self._stop_smart_bar)
        threading.Thread(target=self._smart_worker, daemon=True).start()

    def _animate_smart_bar(self):
        if not getattr(self, "_smart_anim_active", False):
            return
        self._smart_bar_val += 0.025
        if self._smart_bar_val >= 1.0:
            self._smart_bar_val = 1.0
        self.smart_bar.set(self._smart_bar_val)
        if self._smart_bar_val < 1.0:
            self.after(30, self._animate_smart_bar)

    def _stop_smart_bar(self):
        self._smart_anim_active = False
        self.smart_bar.set(1.0)
        self.after(2000, lambda: self.smart_bar.set(0))

    def _smart_worker(self):
        try:
            disks = collect_disks_health()
        except Exception as e:
            disks = []
            write_log(f"SMART: {e}")
        self.after(0, lambda: self._show_smart(disks))

    def _show_smart(self, disks):
        for w in self.smart_scroll.winfo_children():
            w.destroy()
        if not disks:
            ctk.CTkLabel(self.smart_scroll,
                         text="Не удалось получить данные о дисках.\n"
                              "Запустите от имени администратора.",
                         font=("Segoe UI", 13),
                         text_color=THEME["TEXT_DIM"]).pack(pady=40)
            self.smart_status.configure(text="Данные недоступны",
                                        text_color=THEME["AMBER"])
            return
        ok_c = 0
        for d in disks:
            health = d["health"].lower()
            if "healthy" in health or "здоров" in health:
                icon = "✅"
                color = "GREEN"
                ok_c += 1
            elif "warning" in health or "предупр" in health:
                icon = "⚠️"
                color = "AMBER"
            else:
                icon = "❌"
                color = "RED"

            card = ctk.CTkFrame(self.smart_scroll,
                                fg_color=THEME["BG_CARD_HI"], corner_radius=10)
            card.pack(fill="x", padx=8, pady=6)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=14)

            ctk.CTkLabel(row, text=icon,
                         font=("Segoe UI Emoji", 24),
                         text_color=THEME[color]).pack(side="left")

            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", padx=(14, 0), fill="x", expand=True)
            ctk.CTkLabel(txt, text=d["name"],
                         font=("Segoe UI", 14, "bold"),
                         text_color=THEME["TEXT"]).pack(anchor="w")

            media = d["media"].upper() if d["media"] else "—"
            size = f"{d['size_gb']} ГБ" if d["size_gb"] else "—"
            ctk.CTkLabel(txt,
                         text=(f"Тип: {media}  •  Размер: {size}  •  "
                               f"Здоровье: {d['health']}  •  "
                               f"Статус: {d['status']}"),
                         font=("Segoe UI", 11),
                         text_color=THEME["TEXT_SOFT"]).pack(anchor="w",
                                                              pady=(2, 0))

        self.smart_status.configure(
            text=f"Найдено дисков: {len(disks)} • ✅ {ok_c}",
            text_color=THEME["TEXT_SOFT"])
        write_log(f"S.M.A.R.T.: {len(disks)} дисков")

    # ---------- РЕЖИМЫ ----------
    def _build_modes(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["modes"] = page

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 18))
        ctk.CTkLabel(head, text="Режимы работы",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(head, text="Разгоны, экономия и откат твиков",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", pady=(2, 0))

        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.pack(fill="x", padx=28, pady=(0, 16))

        modes = [
            ("🚀", "Высокая производительность",
             "Схема Windows + 100% CPU", "AMBER",
             lambda: self._safe_mode(PowerMode.high_performance)),
            ("⚡", "Разгон процессора",
             "Turbo Boost + сетевой твик", "RED",
             lambda: self._safe_mode(PowerMode.boost_cpu)),
            ("🧠", "Разгон оперативной памяти",
             "Файл подкачки + кэш", "PURPLE",
             lambda: self._safe_mode(PowerMode.boost_ram)),
            ("🎮", "Разгон видеопамяти",
             "GPU + HAGS + PCIe", "GREEN",
             lambda: self._safe_mode(PowerMode.boost_vram)),
            ("📶", "Экономия трафика",
             "Минимум интернета", "CYAN",
             lambda: self._safe_task_mode("экономии трафика")),
            ("🔋", "Экономия энергии",
             "Автономность", "GREEN",
             lambda: self._safe_energy_mode()),
            ("↩️", "Отменить все твики",
             "Вернуть настройки по умолчанию", "PINK",
             lambda: self._safe_mode(PowerMode.revert_all)),
        ]
        self.mode_tiles = []
        for i, (icon, title, subtitle, ckey, cmd) in enumerate(modes):
            tile = ActionTile(grid, icon, title, subtitle, ckey, cmd,
                              mode="mode")
            tile.grid(row=i // 3, column=i % 3,
                      padx=8, pady=8, sticky="nsew")
            grid.grid_columnconfigure(i % 3, weight=1)
            self.mode_tiles.append(tile)

    def _safe_mode(self, fn):
        if not is_admin():
            return "Требуются права администратора"
        ok, msg = fn()
        return msg.split("\n")[0] if ok else f"Ошибка: {msg}"

    def _safe_task_mode(self, mode_name):
        task = self._ask_task(mode_name)
        if not task:
            return "Отменено"
        ok, msg = apply_traffic_saver(task)
        return msg.split("\n")[0] if ok else "Ошибка"

    def _safe_energy_mode(self):
        task = self._ask_task("экономии энергии")
        if not task:
            return "Отменено"
        ok, msg = economy_energy()
        return msg.split("\n")[0] if ok else "Ошибка"

    def _ask_task(self, mode_name):
        dialog = ctk.CTkToplevel(self)
        dialog.title("ProMaster")
        dialog.geometry("520x260")
        dialog.configure(fg_color=THEME["BG_CARD"])
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text=f"Режим {mode_name}",
                     font=("Segoe UI", 18, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w", padx=24,
                                                    pady=(20, 6))
        ctk.CTkLabel(dialog, text="Какую задачу вы собираетесь выполнять?",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", padx=24,
                                                        pady=(0, 12))
        entry = ctk.CTkEntry(dialog, placeholder_text="Например: работа в браузере",
                             width=460, height=38,
                             fg_color=THEME["BG_INPUT"], border_width=0)
        entry.pack(padx=24, pady=(0, 16))
        result = {"value": None}
        def on_ok():
            result["value"] = entry.get().strip() or "универсальная задача"
            dialog.destroy()
        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(padx=24, pady=(8, 20), fill="x")
        ctk.CTkButton(btns, text="Отмена", command=dialog.destroy,
                      fg_color=THEME["BG_INPUT"],
                      hover_color=THEME["BG_CARD_HI"],
                      width=100, height=36).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btns, text="Включить", command=on_ok,
                      fg_color=THEME["ACCENT"],
                      hover_color=THEME["ACCENT_HI"],
                      width=140, height=36).pack(side="right")
        entry.bind("<Return>", lambda e: on_ok())
        entry.focus_set()
        self.wait_window(dialog)
        return result["value"]

    # ---------- БЕЗОПАСНОСТЬ ----------
    def _build_security(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["security"] = page

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 18))
        ctk.CTkLabel(head, text="Безопасность системы",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(head, text="Проверка защитных механизмов Windows",
                     font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", pady=(2, 0))

        radar_card = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"],
                                  corner_radius=16)
        radar_card.pack(fill="x", padx=28, pady=(0, 16))
        self.anim_canvas = tk.Canvas(radar_card, width=400, height=240,
                                     bg=THEME["BG_CARD"], highlightthickness=0)
        self.anim_canvas.pack(pady=20)
        self.animation = SecurityAnimation(
            self.anim_canvas, lambda key: THEME[key])
        self.animation.start()

        btn_row = ctk.CTkFrame(radar_card, fg_color="transparent")
        btn_row.pack(pady=(0, 20))
        self.scan_btn = ctk.CTkButton(
            btn_row, text="🔍  Начать проверку",
            command=self._start_security_scan,
            width=280, height=48, corner_radius=12,
            fg_color=THEME["ACCENT"],
            hover_color=THEME["ACCENT_HI"],
            font=("Segoe UI", 15, "bold"))
        self.scan_btn.pack()
        self.scan_status = ctk.CTkLabel(radar_card, text="Готово к проверке",
                                        font=("Segoe UI", 12),
                                        text_color=THEME["TEXT_DIM"])
        self.scan_status.pack(pady=(0, 16))

        self.results_frame = ctk.CTkScrollableFrame(
            page, fg_color=THEME["BG_CARD"], corner_radius=14)
        self.results_frame.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        enable_smooth_scroll(self.results_frame)
        self.results_placeholder = ctk.CTkLabel(
            self.results_frame,
            text="Здесь появятся рекомендации для вашей защиты",
            font=("Segoe UI", 14), text_color=THEME["TEXT_DIM"])
        self.results_placeholder.pack(pady=40, padx=20)

    def _start_security_scan(self):
        if getattr(self, "_security_running", False):
            return
        self._security_running = True
        self.scan_btn.configure(text="⏳  Проверка…", state="disabled")
        self.scan_status.configure(text="Сканирую систему…",
                                   text_color=THEME["TEXT_DIM"])
        try:
            self.results_placeholder.destroy()
        except Exception:
            pass
        for w in self.results_frame.winfo_children():
            w.destroy()
        threading.Thread(target=self._security_worker, daemon=True).start()

    def _security_worker(self):
        checks = [
            ("Брандмауэр Windows", SecurityChecker.check_firewall,
             SecurityChecker.enable_firewall,
             "Фильтрация входящего и исходящего трафика"),
            ("Защитник Windows", SecurityChecker.check_defender,
             SecurityChecker.enable_defender,
             "Антивирус и защита в реальном времени"),
            ("Контроль учётных записей (UAC)", SecurityChecker.check_uac,
             SecurityChecker.enable_uac,
             "Защита от несанкционированных изменений"),
            ("SmartScreen", SecurityChecker.check_smartscreen, None,
             "Фильтрация подозрительных сайтов"),
        ]
        results = []
        for name, check_fn, fix_fn, desc in checks:
            self.after(0, lambda n=name: self.scan_status.configure(
                text=f"Проверяю: {n}…"))
            time.sleep(0.4)
            ok, msg = check_fn()
            results.append({"name": name, "ok": ok, "msg": msg,
                            "fix": fix_fn, "desc": desc})
        self.after(0, lambda: self._finish_security(results))

    def _finish_security(self, results):
        self._security_running = False
        self.scan_btn.configure(text="🔍  Начать проверку", state="normal")
        problems = [r for r in results if r["ok"] is False]
        warnings = [r for r in results if r["ok"] is None]
        if not problems and not warnings:
            self.scan_status.configure(text="✅ Уязвимостей не найдено",
                                       text_color=THEME["GREEN"])
        else:
            self.scan_status.configure(
                text=(f"⚠️ Проблем: {len(problems)}, "
                      f"предупреждений: {len(warnings)}"),
                text_color=THEME["AMBER"])
        for r in results:
            self._add_result_card(r)

    def _add_result_card(self, r):
        ok = r["ok"]
        icon = "✅" if ok is True else ("❌" if ok is False else "⚠️")
        ck = "GREEN" if ok is True else ("RED" if ok is False else "AMBER")
        card = ctk.CTkFrame(self.results_frame,
                            fg_color=THEME["BG_CARD_HI"], corner_radius=12)
        card.pack(fill="x", padx=8, pady=6)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=14)
        ctk.CTkLabel(row, text=icon, font=("Segoe UI Emoji", 24),
                     text_color=THEME[ck]).pack(side="left")
        tf = ctk.CTkFrame(row, fg_color="transparent")
        tf.pack(side="left", padx=(14, 0), fill="x", expand=True)
        ctk.CTkLabel(tf, text=r["name"], font=("Segoe UI", 14, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(tf, text=r["msg"], font=("Segoe UI", 12),
                     text_color=THEME["TEXT_SOFT"]).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(tf, text=r["desc"], font=("Segoe UI", 11),
                     text_color=THEME["TEXT_DIM"]).pack(anchor="w", pady=(2, 0))
        if ok is False and r["fix"]:
            ctk.CTkButton(row, text="Включить",
                          command=lambda rec=r: self._fix_issue(rec),
                          width=120, height=38, corner_radius=10,
                          fg_color=THEME["GREEN"],
                          hover_color=THEME["ACCENT_HI"],
                          text_color="#000000",
                          font=("Segoe UI", 12, "bold")).pack(
                side="right", padx=(10, 0))

    def _fix_issue(self, rec):
        if not is_admin():
            messagebox.showwarning("ProMaster",
                                   "Для этого нужны права администратора.")
            return
        ok, msg = rec["fix"]()
        if ok:
            messagebox.showinfo("ProMaster", msg)
            self._start_security_scan()
        else:
            messagebox.showerror("ProMaster", f"Ошибка: {msg}")

    # ---------- ЖУРНАЛ ----------
    def _build_log(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["log"] = page
        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 18))
        ctk.CTkLabel(head, text="Журнал операций",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(side="left")
        ctk.CTkButton(head, text="Показать", command=self._reload_log,
                      width=100, height=36, corner_radius=10,
                      fg_color=THEME["BG_CARD"],
                      hover_color=THEME["BG_CARD_HI"],
                      text_color=THEME["TEXT_SOFT"],
                      font=("Segoe UI", 12)).pack(side="right", padx=(8, 0))
        ctk.CTkButton(head, text="Удалить всё", command=self._clear_log,
                      width=120, height=36, corner_radius=10,
                      fg_color=THEME["BG_CARD"],
                      hover_color=THEME["BG_CARD_HI"],
                      text_color=THEME["TEXT_SOFT"],
                      font=("Segoe UI", 12)).pack(side="right", padx=(8, 0))
        self.log = ctk.CTkTextbox(page, font=("Consolas", 12),
                                  fg_color=THEME["BG_CARD"], corner_radius=14,
                                  text_color=THEME["TEXT"])
        self.log.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        self._reload_log()

    def _reload_log(self):
        try:
            self.log.delete("1.0", "end")
        except Exception:
            return
        for line in read_log_tail(500):
            self.log.insert("end", line)
        self.log.see("end")

    def _clear_log(self):
        if not messagebox.askyesno("ProMaster", "Удалить все записи?"):
            return
        try:
            open(LOG_FILE, "w", encoding="utf-8").close()
        except Exception:
            pass
        self._reload_log()

    # ---------- НАСТРОЙКИ ----------
    def _build_settings(self):
        page = ctk.CTkFrame(self.content, fg_color=THEME["BG"])
        self.pages["settings"] = page
        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(24, 18))
        ctk.CTkLabel(head, text="Настройки",
                     font=("Segoe UI", 26, "bold"),
                     text_color=THEME["TEXT"]).pack(anchor="w")

        card2 = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"], corner_radius=14)
        card2.pack(fill="x", padx=28, pady=(0, 12))
        ctk.CTkLabel(card2, text="Информация",
                     font=("Segoe UI", 13, "bold"),
                     text_color=THEME["TEXT_SOFT"]).pack(anchor="w", padx=20,
                                                          pady=(18, 8))
        for line in ["ProMaster 12.4",
                     "Мониторинг, очистка, безопасность, разгоны, драйверы",
                     "Автор: ProMaster Team"]:
            ctk.CTkLabel(card2, text=line, text_color=THEME["TEXT_SOFT"],
                         font=("Segoe UI", 12)).pack(anchor="w", padx=20,
                                                     pady=2)
        ctk.CTkFrame(card2, fg_color="transparent", height=12).pack()

        # Блок благодарности
        thanks_card = ctk.CTkFrame(page, fg_color=THEME["BG_CARD"],
                                   corner_radius=14)
        thanks_card.pack(fill="x", padx=28, pady=(0, 20))
        inner = ctk.CTkFrame(thanks_card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=32, pady=28)

        ctk.CTkLabel(inner,
                     text="💙  Спасибо, что выбрали ProMaster",
                     font=("Segoe UI", 20, "bold"),
                     text_color=THEME["ACCENT_HI"],
                     anchor="w").pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(
            inner,
            text=("Я делаю бесплатное ПО для русскоязычных пользователей "
                  "и против навязывания рекламы.\n"
                  "Буду рад поддержке на баланс телефона — сумма любая.\n"
                  "Готов написать программу на заказ."),
            font=("Segoe UI", 13),
            text_color=THEME["TEXT_SOFT"],
            justify="left",
            anchor="w").pack(anchor="w", pady=(0, 18))

        contacts = ctk.CTkFrame(inner, fg_color=THEME["BG_CARD_HI"],
                                corner_radius=10)
        contacts.pack(fill="x")

        row1 = ctk.CTkFrame(contacts, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=(14, 6))
        ctk.CTkLabel(row1, text="📧  Почта:",
                     font=("Segoe UI", 12),
                     text_color=THEME["TEXT_DIM"],
                     width=110, anchor="w").pack(side="left")
        ctk.CTkLabel(row1, text="Alesker85@yandex.ru",
                     font=("Segoe UI", 14, "bold"),
                     text_color=THEME["ACCENT_HI"],
                     anchor="w").pack(side="left", padx=(8, 0))

        row2 = ctk.CTkFrame(contacts, fg_color="transparent")
        row2.pack(fill="x", padx=20, pady=(6, 14))
        ctk.CTkLabel(row2, text="📞  Телефон:",
                     font=("Segoe UI", 12),
                     text_color=THEME["TEXT_DIM"],
                     width=110, anchor="w").pack(side="left")
        ctk.CTkLabel(row2, text="8 (917) 917-72-77",
                     font=("Segoe UI", 14, "bold"),
                     text_color=THEME["GREEN"],
                     anchor="w").pack(side="left", padx=(8, 0))

    # ---------- МОНИТОРИНГ ----------
    def _refresh(self):
        try:
            cpu = psutil.cpu_percent()
            self.ring_cpu.set(cpu, f"{cpu:.0f}%", "загружено")

            mem = psutil.virtual_memory()
            used_gb = (mem.total - mem.available) / (1024 ** 3)
            total_gb = mem.total / (1024 ** 3)
            self.ring_ram.set(mem.percent, f"{mem.percent:.0f}%",
                              f"{used_gb:.1f} / {total_gb:.1f} ГБ")

            try:
                d = psutil.disk_usage(system_drive())
                used_d = (d.total - d.free) / (1024 ** 3)
                total_d = d.total / (1024 ** 3)
                self.ring_disk.set(d.percent, f"{d.percent:.0f}%",
                                   f"{used_d:.0f} / {total_d:.0f} ГБ")
            except Exception:
                self.ring_disk.set(0, "N/A", "")

            vram_bytes = self.hw.get("vram_bytes", 0)
            if vram_bytes > 0:
                vram_gb = vram_bytes / (1024 ** 3)
                self.ring_vram.set(0, f"{vram_gb:.1f}", "ГБ видеопамяти")
            else:
                self.ring_vram.set(0, "N/A", "")

            self.c_proc.set(f"{len(psutil.pids())}")

            up_sec = time.time() - psutil.boot_time()
            hh, mm = int(up_sec // 3600), int((up_sec % 3600) // 60)
            self.c_upt.set(f"{hh} ч {mm} мин")

            self._refresh_disks()
        except Exception:
            pass
        self.after(1000, self._refresh)

    def _refresh_disks(self):
        try:
            parts = [p for p in psutil.disk_partitions()
                     if p.fstype and "cdrom" not in p.opts.lower()]
        except Exception:
            return
        current = getattr(self, "_disk_labels", None)
        if current is None or len(current) != len(parts):
            for w in self.disk_rows.winfo_children():
                w.destroy()
            self._disk_labels = []
            for p in parts:
                row = ctk.CTkFrame(self.disk_rows, fg_color="transparent")
                row.pack(fill="x", pady=4)
                name = p.device.rstrip("\\")
                ctk.CTkLabel(row, text=name, width=60,
                             text_color=THEME["TEXT"],
                             font=("Segoe UI", 12, "bold")).pack(side="left")
                info = ctk.CTkLabel(row, text="",
                                    text_color=THEME["TEXT_SOFT"],
                                    font=("Segoe UI", 11), width=380)
                info.pack(side="left", padx=(8, 12))
                bar = ctk.CTkProgressBar(row, height=8, corner_radius=4,
                                         progress_color=THEME["PINK"], width=300)
                bar.pack(side="left", padx=(0, 12))
                bar.set(0)
                pct = ctk.CTkLabel(row, text="--", width=60,
                                   text_color=THEME["TEXT_DIM"],
                                   font=("Segoe UI", 11))
                pct.pack(side="left")
                self._disk_labels.append({
                    "path": p.mountpoint, "info": info,
                    "bar": bar, "pct": pct,
                })
        for item in self._disk_labels:
            try:
                d = psutil.disk_usage(item["path"])
                used = (d.total - d.free) / (1024 ** 3)
                total = d.total / (1024 ** 3)
                free = d.free / (1024 ** 3)
                item["info"].configure(
                    text=(f"Занято {used:.0f} ГБ • "
                          f"Свободно {free:.0f} ГБ из {total:.0f} ГБ"))
                item["bar"].set(d.percent / 100)
                item["pct"].configure(text=f"{d.percent:.0f}%")
            except Exception:
                item["info"].configure(text="Недоступен")


if __name__ == "__main__":
    app = App()
    app.mainloop()