import os

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

empty_set = {}

def get_extension(file_path):
    return os.path.splitext(file_path)

def target_os(file_path):
    ext = get_extension(file_path)
    return target_os(ext)

def target_os_ext(ext):
    if ext in extensionToOperatingSystem:
        return extensionToOperatingSystem[ext]
    return empty_set

def matches(ext, os):
    return os in target_os_ext(ext)  
