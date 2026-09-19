from os import listdir, path  # listdir: 列出目录中的文件；path: 用于处理文件路径和文件名
from typing import List

def readname(file_path: str):
    """
    读取指定文件中的所有行，并以列表形式返回。
    每行作为一个元素，去除换行符。

    参数:
        file_path (str): 要读取的文件的路径

    返回:
        list: 文件中每一行的内容组成的列表（去除换行符）
    """
    with open(file_path, "r", encoding="utf-8") as fp:  # 以 UTF-8 编码打开文件
        return fp.read().split("\n")  # 读取全部内容并按换行符分割成列表

def read_filename(file_path: str) -> list:
    """
    获取指定目录下所有文件的文件名（不含后缀名）。

    参数:
        file_path (str): 目录路径

    返回:
        list: 包含该目录下所有文件（不含子目录）的文件名（去除后缀）的列表
    """
    # 获取目录下的所有文件和子目录的名称列表
    files = listdir(file_path)
    
    # 遍历所有项目，仅保留文件（排除目录），并去除文件扩展名
    # path.splitext(file)[0] 提取文件名部分（不含后缀）
    # path.join(file_path, file) 构造完整路径用于判断是否为文件
    name_list = [
        path.splitext(file)[0] 
        for file in files 
        if path.isfile(path.join(file_path, file))
    ]
    
    return name_list  # 返回文件名（无后缀）列表


def formar_names(names: List[str], per_line: int) -> str:
    """
    将名字列表格式化为多行字符串，每行最多显示 per_line 个名字，按字典序排序。

    参数:
        names (List[str]): 名字列表。
        per_line (int): 每行显示的名字数量。

    返回:
        str: 格式化后的字符串，每行由空格分隔，行间用换行符连接。

    示例:
        formar_names(['c', 'a', 'b', 'd'], 2) -> "a b\nc d"
    """
    if per_line < 1:
        raise ValueError("per_line 必须大于等于 1")

    name_list = sorted(names)  # 排序
    result = []

    # 每 per_line 个元素一组
    for i in range(0, len(name_list), per_line):
        line = ' '.join(name_list[i:i + per_line])
        result.append(line)

    return '\n'.join(result)
