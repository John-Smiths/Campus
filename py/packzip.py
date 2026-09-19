import zipfile
import asyncio
from pathlib import Path
from shutil import rmtree
from concurrent.futures import ThreadPoolExecutor
import os


def create_zip_from_folder(folder_path, zip_filename, compression=zipfile.ZIP_DEFLATED):
    """
    快速压缩文件夹
    
    Args:
        folder_path: 要压缩的文件路径
        zip_filename: 要输出的名称与地址
        compression: 压缩算法，默认 ZIP_DEFLATED（推荐）
    """
    folder_path = Path(folder_path)
    
    # 预收集所有文件（避免在写入时重复遍历）
    files_to_zip = []
    for file_path in folder_path.rglob('*'):
        if file_path.is_file():
            files_to_zip.append((file_path, file_path.relative_to(folder_path)))
    
    # 一次性写入，使用压缩
    with zipfile.ZipFile(zip_filename, 'w', compression=compression) as zipf:
        for file_path, arcname in files_to_zip:
            zipf.write(file_path, arcname)
    
    print(f"✓ 已压缩 {len(files_to_zip)} 个文件到 {zip_filename}")


async def create_zip_from_folder_async(folder_path, zip_filename, compression=zipfile.ZIP_DEFLATED):
    """
    异步压缩文件夹（适合大量文件）
    
    Args:
        folder_path: 要压缩的文件路径
        zip_filename: 要输出的名称与地址
        compression: 压缩算法
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, 
        create_zip_from_folder, 
        folder_path, 
        zip_filename, 
        compression
    )


def delete_files_in_directory(directory, keep_subdirs=True):
    """
    快速删除目录中的文件
    
    Args:
        directory: 目标目录
        keep_subdirs: 是否保留子目录（默认True）
    """
    directory = Path(directory)
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.")
        return
    
    deleted_count = 0
    failed_count = 0
    
    # 使用 iterdir() 代替 listdir，性能更好
    for item in directory.iterdir():
        if item.is_file():
            try:
                item.unlink()  # 比 os.remove() 更快
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete {item}. Reason: {e}")
                failed_count += 1
        elif item.is_dir() and keep_subdirs:
            continue  # 跳过子目录
    
    print(f"✓ 删除了 {deleted_count} 个文件" + (f", 失败 {failed_count} 个" if failed_count else ""))


async def delete_files_in_directory_async(directory, keep_subdirs=True, max_workers=4):
    """
    异步并发删除文件（适合大量文件）
    
    Args:
        directory: 目标目录
        keep_subdirs: 是否保留子目录
        max_workers: 最大并发数
    """
    directory = Path(directory)
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.")
        return
    
    # 收集要删除的文件
    files_to_delete = [item for item in directory.iterdir() if item.is_file()]
    
    if not files_to_delete:
        print("没有文件需要删除")
        return
    
    # 并发删除
    def delete_file(file_path):
        try:
            file_path.unlink()
            return True
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")
            return False
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = await asyncio.gather(*[
            loop.run_in_executor(executor, delete_file, f)
            for f in files_to_delete
        ])
    
    deleted_count = sum(results)
    print(f"✓ 删除了 {deleted_count}/{len(files_to_delete)} 个文件")


def delete_directory(file_path):
    """
    删除整个目录（包括所有内容）
    
    Args:
        file_path: 要删除的目录路径
    """
    file_path = Path(file_path)
    
    if file_path.exists():
        if file_path.is_dir():
            rmtree(file_path)
            print(f"✓ 已删除目录: {file_path}")
        else:
            print(f"Warning: '{file_path}' 不是目录")
    else:
        print(f"Info: '{file_path}' 不存在，无需删除")


def delete_directory_silent(file_path):
    """
    静默删除目录（不输出任何信息）
    
    Args:
        file_path: 要删除的目录路径
    """
    file_path = Path(file_path)
    if file_path.exists() and file_path.is_dir():
        rmtree(file_path)


# 批量操作优化
def batch_delete_files(file_list, max_workers=4):
    """
    批量删除文件（多线程）
    
    Args:
        file_list: 文件路径列表
        max_workers: 最大线程数
    """
    def delete_single(file_path):
        try:
            Path(file_path).unlink()
            return True
        except:
            return False
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(delete_single, file_list))
    
    success = sum(results)
    print(f"✓ 批量删除: {success}/{len(file_list)} 个文件成功")


# 使用示例
if __name__ == '__main__':
    # 同步使用
    create_zip_from_folder('my_folder', 'output.zip')
    delete_files_in_directory('temp_folder')
    delete_directory('old_folder')
    
    # 异步使用（推荐用于大量文件）
    async def async_example():
        await create_zip_from_folder_async('large_folder', 'output.zip')
        await delete_files_in_directory_async('temp_folder', max_workers=8)
    
    # asyncio.run(async_example())
