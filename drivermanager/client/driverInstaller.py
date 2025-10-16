"""
Универсальный инсталлятор драйверов

Поддерживаемые расширения: .exe, .msi, .inf, .run, .tar, .tar.gz, .deb
Поведение (по умолчанию):
  - Windows:
      .exe  -> запускаем с '/S' (можно переопределить через installer_args)
      .msi  -> msiexec /i <file> /qn
      .inf  -> pnputil -i -a <file>  (fallback: dism /online /add-driver /driver:<file>)
  - Linux:
      .deb  -> sudo dpkg -i <file> (и попытка apt-get -f install при ошибке)
      .run  -> sudo bash <file>
      .tar* -> распаковать tar -> если в распаковке есть install.sh или setup.sh, запустить
"""

import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import argparse
import shutil
import common.fileManager as fm

LOGGER_NAME = "driver_installer"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(LOGGER_NAME)

extensionToOperatingSystem = {
    ".exe": {"windows"},
    ".msi": {"windows"},
    ".inf": {"windows"},
    ".run": {"linux"},
    ".tar": {"linux"},
    ".gz": {"linux"},
    ".deb": {"linux"},
    ".rpm": {"linux"}
}

DEFAULT_INSTALL_TIMEOUT = 300

# ---------- Выполнение команд / установка ----------
class InstallResult:
    def __init__(self, success: bool, code: int = 0, stdout: str = "", stderr: str = "", reason: str = ""):
        self.success = success
        self.code = code
        self.stdout = stdout
        self.stderr = stderr
        self.reason = reason

    def as_dict(self) -> Dict:
        return {
            "success": self.success,
            "code": self.code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "reason": self.reason
        }


def _run_cmd(cmd: List[str], timeout: int = DEFAULT_INSTALL_TIMEOUT) -> InstallResult:
    logger.info("Running command: %s", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        success = proc.returncode == 0
        return InstallResult(success, proc.returncode, proc.stdout or "", proc.stderr or "")
    except subprocess.TimeoutExpired as e:
        logger.error("Timeout running %s", cmd)
        return InstallResult(False, code=-1, stdout=e.stdout or "", stderr=str(e), reason="timeout")
    except Exception as e:
        logger.exception("Exception running command")
        return InstallResult(False, code=-2, stderr=str(e), reason="exception")


def _windows_install(file_path: str, ext: str, installer_args: Optional[List[str]] = None) -> InstallResult:
    p = Path(file_path)
    installer_args = installer_args or []
    if ext == ".inf":
        # prefer pnputil, fallback to dism
        pnputil = Path(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), f"System32", "pnputil.exe"))
        if pnputil.exists():
            cmd = [str(pnputil), "-i", "-a", str(p)]
            return _run_cmd(cmd)
        else:
            cmd = ["dism", "/online", "/add-driver", f"/driver:{str(p)}", "/install"]
            return _run_cmd(cmd)
    elif ext == ".msi":
        # msiexec /i file.msi /qn
        cmd = ["msiexec", "/i", str(p), "/qn"] + installer_args
        return _run_cmd(cmd)
    elif ext == ".exe":
        # common silent switches vary: /S, /quiet, /silent. Use provided installer_args or default '/S'
        args = [] # installer_args if installer_args else ["/S"]
        cmd = [str(p)] + args
        return _run_cmd(cmd)
    else:
        return InstallResult(False, reason=f"Unsupported windows extension: {full_ext}")


def _linux_install(file_path: str, ext: str, installer_args: Optional[List[str]] = None) -> InstallResult:
    p = Path(file_path)
    installer_args = installer_args or []
    if ext == ".deb":
        cmd = ["sudo", "dpkg", "-i", str(p)]
        res = _run_cmd(cmd)
        if not res.success:
            logger.info("dpkg failed, attempting apt-get -f install to fix dependencies")
            fix = _run_cmd(["sudo", "apt-get", "-y", "install", "-f"])
            if fix.success:
                res = _run_cmd(cmd)
        return res
    elif ext == ".rpm":
        return _run_cmd(["sudo", "rpm", "-Uvh", str(p)])
    elif ext == ".run":
        # make executable then run with bash (installer_args appended)
        try:
            p.chmod(p.stat().st_mode | 0o111)
        except Exception:
            logger.warning("Failed to chmod +x %s", p)
        cmd = ["sudo", "bash", str(p)] + installer_args
        return _run_cmd(cmd)
    elif ext == "tar" or ext == "gz":
        # Extract to temp dir and try to find installer scripts
        tmpdir = Path("/tmp/driver_install_" + p.stem)
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
        tmpdir.mkdir(parents=True, exist_ok=True)
        logger.info("Extracting %s to %s", p, tmpdir)
        # support .tar, .tar.gz, .tar.bz2 etc - let tar autodetect
        res = _run_cmd(["tar", "-xvf", str(p), "-C", str(tmpdir)])
        if not res.success:
            return res
        # scan for common installer scripts
        for script in ("install.sh", "setup.sh", "install"):
            found = tmpdir / script
            if found.exists():
                try:
                    found.chmod(found.stat().st_mode | 0o111)
                except Exception:
                    pass
                return _run_cmd(["sudo", "bash", str(found)] + installer_args)
        return InstallResult(True, reason="extracted_only", stdout=f"Extracted to {tmpdir}")
    else:
        return InstallResult(False, reason=f"Unsupported linux extension: {full_ext}")


def install_driver(file_path: str, installer_args: Optional[List[str]] = None) -> InstallResult:
    """
    Основная точка: вызывает установку в зависимости от текущей ОС.
    installer_args — дополнительные аргументы, передаваемые инсталлятору.
    """
    if not os.path.exists(file_path):
        return InstallResult(False, reason="file_not_found")

    system = platform.system().lower()  # 'windows', 'linux', 'darwin' ...
    ext = fm.get_extension(file_path)
    logger.info("Detected system=%s, file_ext=%s", system, ext)

    if system.startswith("win"):
        # проверка соответствия расширения к ОС (опционально)
        if not fm.matches(ext, "windows"):
            logger.warning("File extension %s not listed for windows, attempting anyway", ext)
        return _windows_install(file_path, ext, installer_args)
    elif system.startswith("linux"):
        if not fm.matches(ext, "linux"):
            logger.warning("File extension %s not listed for linux, attempting anyway", ext)
        return _linux_install(file_path, ext, installer_args)
    else:
        return InstallResult(False, reason=f"Unsupported platform: {system}")


# ---------- Пакетная установка ----------
def install_drivers(files: List[str], common_installer_args: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Устанавливает список файлов по очереди.
    Возвращает словарь {filename: InstallResult.as_dict()}
    """
    results = {}
    for f in files:
        logger.info("Starting installation for %s", f)
        try:
            res = install_driver(f, common_installer_args)
            results[f] = res.as_dict()
            logger.info("Result for %s: %s", f, results[f])
        except Exception as e:
            logger.exception("Unhandled exception while installing %s", f)
            results[f] = {"success": False, "reason": "exception", "stderr": str(e)}
    return results


# ---------- CLI (для тестирования) ----------
def _parse_args():
    p = argparse.ArgumentParser(description="Driver batch installer (Windows/Linux)")
    p.add_argument("files", nargs="+", help="Paths to driver files to install")
    p.add_argument("--args", nargs="*", help="Common installer args to append", default=[])
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main():
    args = _parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    results = install_drivers(args.files, args.args)
    for fname, info in results.items():
        print(f"=== {fname} ===")
        print(f"Success: {info.get('success')}")
        if info.get("reason"):
            print(f"Reason: {info.get('reason')}")
        if info.get("stdout"):
            print("--- stdout ---")
            print(info.get("stdout"))
        if info.get("stderr"):
            print("--- stderr ---")
            print(info.get("stderr"))
        print()

if __name__ == "__main__":
    main()
