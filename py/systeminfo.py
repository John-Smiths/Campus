import psutil
import datetime
import time
import os

NETWORK_SYMBOLS = ["B", "KB", "MB", "GB", "TB"]

def get_system_resources():
    # 获取CPU使用率
    cpu_percent = psutil.cpu_percent(interval=True)

    # 获取内存信息
    memory_info = psutil.virtual_memory()
    mem_percent = memory_info.percent  # 内存使用百分比
    swap_info = psutil.swap_memory()  # 虚拟内存信息
    swap_percent = swap_info.percent  # 虚拟内存使用百分比

    # 获取磁盘使用情况，这里以根目录'/'为例
    disk_usage = psutil.disk_usage('/')
    disk_percent = disk_usage.percent  # 硬盘使用百分比

    # 获取网络统计信息，计算开机以来的网络使用量
    net_io_counters = psutil.net_io_counters()
    bytes_sent = net_io_counters.bytes_sent
    bytes_recv = net_io_counters.bytes_recv
    
    n = 0
    while bytes_sent > 1024:
        bytes_sent = bytes_sent / 1024
        n += 1
    bytes_sent = f"{bytes_sent:.2f} {NETWORK_SYMBOLS[n]}"

    n = 0
    while bytes_recv > 1024:
        bytes_recv = bytes_recv / 1024
        n += 1
    bytes_recv = f"{bytes_recv:.2f} {NETWORK_SYMBOLS[n]}"



    # 计算开机时间
    boot_time_timestamp = psutil.boot_time()
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time_timestamp)
    uptime_days = uptime.days

    return {
        'cpu_percent': cpu_percent,
        'mem_percent': mem_percent,
        'swap_percent': swap_percent,
        'disk_percent': disk_percent,
        'network_sent': bytes_sent,
        'network_recv': bytes_recv,
        'uptime_days': uptime_days
    }

def systeminfo():
    resources = get_system_resources()

    data = ""

    data +=(f"CPU 使用率: {resources['cpu_percent']}%\n")
    data +=(f"内存使用率: {resources['mem_percent']}%\n")
    data +=(f"交换分区使用率: {resources['swap_percent']}%\n")
    data +=(f"磁盘使用率: {resources['disk_percent']}%\n")
    data +=(f"网络发送: {resources['network_sent']}\n")
    data +=(f"网络接收: {resources['network_recv']}\n")
    data +=(f"正常运行时间: {resources['uptime_days']} 天\n")
    return data

def get_len_number(directory):
    """
    返回指定目录下的文件数量。

    :param directory: 要统计的目录路径
    :return: 文件数量
    """
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    return len(files)
