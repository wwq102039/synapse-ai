import json
import platform
import os
import time
import sys
from datetime import datetime
from . import register


@register(
    "system_info",
    "获取系统信息：操作系统、CPU、内存、磁盘、Python 版本、运行时间。用于了解运行环境。",
    {"info_type": {"type": "string", "description": "信息类型：'overview'（概览）、'cpu'、'memory'（内存）、'disk'（磁盘）、'network'（网络）或 'all'（全部）"}}
)
def system_info(info_type: str = "overview") -> str:
    try:
        info = {}
        if info_type in ("overview", "all"):
            info["platform"] = platform.platform()
            info["system"] = platform.system()
            info["release"] = platform.release()
            info["machine"] = platform.machine()
            info["processor"] = platform.processor()
            info["python_version"] = sys.version
            info["hostname"] = platform.node()
            info["current_time"] = datetime.now().isoformat()
            info["cwd"] = os.getcwd()

        if info_type in ("cpu", "all"):
            info["cpu_count"] = os.cpu_count()
            if hasattr(os, "sched_getaffinity"):
                try:
                    info["cpu_available"] = len(os.sched_getaffinity(0))
                except Exception:
                    pass

        if info_type in ("memory", "all"):
            try:
                import psutil
                mem = psutil.virtual_memory()
                info["memory"] = {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "available_gb": round(mem.available / (1024**3), 2),
                    "percent_used": mem.percent,
                }
            except ImportError:
                info["memory"] = "psutil not installed"

        if info_type in ("disk", "all"):
            try:
                import psutil
                disk = psutil.disk_usage("/")
                info["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": disk.percent,
                }
            except ImportError:
                info["disk"] = "psutil not installed"

        if info_type in ("network", "all"):
            try:
                import psutil
                net = psutil.net_if_addrs()
                info["network_interfaces"] = list(net.keys())
            except ImportError:
                info["network_interfaces"] = "psutil not installed"

        return json.dumps(info, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})
