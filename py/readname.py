from os import listdir, path
def readname(file_path:str):
    with open(file_path, "r") as fp:
        return fp.read().split("\n")

def istrue(raw_list:list, constant):
    for i in raw_list:
        if i == constant:
            return True  # 存在

    return False  # 不存在

def read_filename(file_path: str) -> list:
    # 获取目录下的所有文件名
    files = listdir(file_path)
    
    # 去除文件后缀名
    name_list = [path.splitext(file)[0] for file in files if path.isfile(path.join(file_path, file))]
    
    return name_list
