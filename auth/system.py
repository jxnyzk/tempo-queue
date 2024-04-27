import hashlib
import platform
import socket
import subprocess

def GetCpuID():
    cpuid = ""
    if platform.system().lower() == "linux":
        cpuid = getLinuxSystemID()
    elif platform.system().lower() == "windows":
        cpuid = getWindowsCpuID()
    else:
        raise Exception("unsupported operating system: {}".format(platform.system()))
    return cpuid

def getLinuxSystemID():
    hostname = socket.gethostname()
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuInfo = f.read()
    except:
        return ""
    systemID = hashlib.sha256("{}|{}".format(hostname, cpuInfo).encode()).hexdigest()
    return systemID

def getWindowsCpuID():
    try:
        output = subprocess.check_output(["wmic", "cpu", "get", "ProcessorId"]).decode()
        output = output.replace("ProcessorId", "").strip()
    except Exception as e:
        print("Error executing command:", e)
        return ""
    return output