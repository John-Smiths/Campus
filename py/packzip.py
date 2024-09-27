import zipfile
from os import path, walk, listdir
from shutil import rmtree

def create_zip_from_folder(folder_path, zip_filename):
    """
    folder_path (path) 要压缩的文件路径
    zip_filename (zip name) 要输出的名称与地址
    """
    # 创建一个 ZipFile 对象，并以写入模式打开一个新ZIP文件
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        # 遍历指定的文件夹
        for root, dirs, files in walk(folder_path):
            for file in files:
                # 获取文件完整路径
                file_path = path.join(root, file)
                # 在ZIP文件中存储文件，使用相对路径（从folder_path开始）
                zipf.write(file_path, os.path.relpath(file_path, folder_path))

def delete_files_in_directory(directory):
    # 首先检查给定的路径是否为目录
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a directory.")
        return
    
    # 遍历顶层目录下的文件和子目录
    for item in listdir(directory):
        item_path = path.join(directory, item)
        
        # 如果是文件，则删除它
        if path.isfile(item_path):
            try:
                remove(item_path)
                print(f"Deleted file: {item_path}")
            except Exception as e:
                print(f"Failed to delete {item_path}. Reason: {e}")
                
        # 如果是子目录，则跳过
        elif path.isdir(item_path):
            print(f"Skipped subdirectory: {item_path}")

def delete_directory(file_path):
    if path.exists(file_path):
        rmtree(file_path)
    else:
        pass
