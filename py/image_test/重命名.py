import os
import shutil

def rename_jpg_files(directory='.'):
    # 获取指定目录下所有的.jpg文件
    jpg_files = [f for f in os.listdir(directory) if f.lower().endswith('.jpg')]
    
    # 按照文件名排序（这里假设你想要按照原有的顺序）
    jpg_files.sort()
    
    # 重命名文件
    for index, old_name in enumerate(jpg_files, start=1):
        new_name = f"{index}.jpg"
        old_file_path = os.path.join(directory, old_name)
        new_file_path = os.path.join(directory, new_name)
        
        # 如果新文件名已经存在，则跳过或采取其他措施
        if not os.path.exists(new_file_path):
            shutil.move(old_file_path, new_file_path)
            print(f"Renamed '{old_name}' to '{new_name}'")
        else:
            print(f"Skipped renaming '{old_name}', because '{new_name}' already exists.")

# 调用函数，默认参数为当前目录
rename_jpg_files()
