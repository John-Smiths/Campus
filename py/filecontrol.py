from os import listdir, path, remove, makedirs
from shutil import rmtree  # 用于删除整个目录树
from typing import List

def flie_control(file_path: str, class_name: str, task_id: str, code: bool):
    """
    根据给定参数创建或清空指定目录。

    如果 code 为 True：
        创建路径格式为 '{class_name}+{file_path}+{task_id}' 的文件夹（支持多级路径）。
        若目录已存在，不报错。

    如果 code 为 False：
        删除路径 '{class_name}+{file_path}+{task_id}' 下的所有内容（包括文件和子目录）。
        注意：仅清空内容，不删除该目录本身；若目录不存在则无操作。

    参数:
        file_path (str): 基础路径部分。
        class_name (str): 班级名称，用于构成目录名。
        task_id (str): 任务 ID，用于构成目录名。
        code (bool): 控制行为，True 表示创建目录，False 表示清空目录内容。

    异常:
        可能抛出 OSError 及其子类异常（如权限不足等），调用方需注意处理。
    """
    # 构造目录路径
    directory = f'{class_name}+{file_path}+{task_id}'

    if code:
        # 创建目录（包括多级）
        makedirs(directory, exist_ok=True)
    else:
        # 清空目录下的所有内容（文件和文件夹）
        if not path.exists(directory):
            return  # 目录不存在，无需操作

        if not path.isdir(directory):
            raise NotADirectoryError(f"路径 {directory} 不是一个目录，无法清空内容。")

        # 遍历目录下所有项目
        for item in listdir(directory):
            item_path = path.join(directory, item)
            try:
                if path.isfile(item_path) or path.islink(item_path):
                    remove(item_path)  # 删除文件或符号链接
                elif path.isdir(item_path):
                    rmtree(item_path)  # 删除整个子目录
            except Exception as e:
                print(f"警告：删除 {item_path} 时出错：{e}")
                # 继续删除其他文件，不中断整体流程

def read_filename(file_path: str) -> List[str]:
    """
    获取指定目录下所有文件的文件名（不含扩展名）。

    参数:
        file_path (str): 目录路径。

    返回:
        List[str]: 包含目录中所有文件（非目录）的文件名（去除扩展名后）的列表。

    异常:
        FileNotFoundError: 如果目录不存在。
        NotADirectoryError: 如果路径存在但不是目录。
        PermissionError: 无权限访问目录。
    """
    if not path.exists(file_path):
        raise FileNotFoundError(f"目录不存在: {file_path}")
    if not path.isdir(file_path):
        raise NotADirectoryError(f"路径不是目录: {file_path}")

    files = listdir(file_path)
    # 拼接完整路径并判断是否为文件，提取文件名（无扩展名）
    name_list = [
        path.splitext(file)[0]
        for file in files
        if path.isfile(path.join(file_path, file))
    ]
    return name_list
