import os
from PIL import Image
from imagehash import phash
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor

def get_image_block_hashes(image_path, num_blocks=10, crop_ratio=0.05, use_parallel=True):
    """
    打开指定路径的图像，分割成块，并返回每个块的感知哈希值。
    
    :param image_path: 图像文件的路径
    :param num_blocks: 分割的块数（假设是平方根）
    :param crop_ratio: 裁剪比例（0 到 1），表示从顶部裁剪的高度比例
    :param use_parallel: 是否使用并行处理计算哈希值
    :return: 图像的分块 pHash 值列表, 未处理图片损坏
    """
    # 优化1: 使用 'r' 模式快速读取，避免不必要的解码
    with Image.open(image_path) as img:
        # 优化2: 如果需要裁剪，直接在打开时处理
        if crop_ratio > 0:
            width, height = img.size
            crop_height = int(height * crop_ratio)
            img = img.crop((0, 0, width, crop_height))
        # 优化3: 转换为 RGB（如果需要），避免后续重复转换
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        # 分割图像成块
        blocks = split_image_into_blocks(img, num_blocks)
    # 优化4: 并行计算哈希值（如果块数较多）
    if use_parallel and len(blocks) > 4:
        with ThreadPoolExecutor(max_workers=min(len(blocks), 8)) as executor:
            block_hashes = list(executor.map(phash, blocks))
    else:
        block_hashes = [phash(block) for block in blocks]
    
    return block_hashes

def get_image_block_hashes_optimized(image_path, num_blocks=10, crop_ratio=0.05):
    """
    进一步优化版本：减少内存拷贝，使用 numpy 数组直接操作。如果图片损坏，则返回 False。

    :param image_path: 图像文件的路径
    :param num_blocks: 分割的块数（假设是平方根）
    :param crop_ratio: 裁剪比例（0 到 1），表示从顶部裁剪的高度比例
    :return: 如果成功，则返回图像的分块 pHash 值列表；如果图像损坏，则返回 False
    """
    try:
        # 尝试打开图片
        with Image.open(image_path) as img:
            pass
    except IOError:
        # 如果图片无法打开/加载，返回 False
        return False

    try:
        with Image.open(image_path) as img:
            # 裁剪
            if crop_ratio > 0:
                width, height = img.size
                crop_height = int(height * crop_ratio)
                img = img.crop((0, 0, width, crop_height))
            # 转换为统一格式
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            # 转换为 numpy 数组以便快速切片
            img_array = np.array(img)

            # 计算块的尺寸
            height, width = img_array.shape[:2]
            block_height = height // num_blocks
            block_width = width // num_blocks

            # 使用列表推导式和 numpy 切片快速生成块
            blocks = []
            for i in range(num_blocks):
                for j in range(num_blocks):
                    y_start = i * block_height
                    y_end = (i + 1) * block_height if i < num_blocks - 1 else height
                    x_start = j * block_width
                    x_end = (j + 1) * block_width if j < num_blocks - 1 else width

                    block_array = img_array[y_start:y_end, x_start:x_end]
                    blocks.append(Image.fromarray(block_array))

            # 并行计算哈希
            with ThreadPoolExecutor(max_workers=min(len(blocks), 8)) as executor:
                block_hashes = list(executor.map(phash, blocks))

            return block_hashes
    except Exception as e:
        # 捕获其他可能的异常，并返回 False
        print(f"处理图片 {image_path} 时发生错误: {e}")
        return False

def calculate_match_degree(hashes1, hashes2):
    """
    计算两个分块哈希值列表之间的匹配度。
    :param hashes1: 第一个图像的分块 pHash 值列表
    :param hashes2: 第二个图像的分块 pHash 值列表
    :return: 综合匹配度（0 到 1 之间的浮点数，1 表示完全匹配）
    """
    # 如果两个列表长度不一致，则无法进行比较，返回0.0
    if len(hashes1) != len(hashes2):
        return 0.0

    total_match_degree = 0.0
    for hash1, hash2 in zip(hashes1, hashes2):
        # 计算汉明距离
        hamming_distance = hash1 - hash2
        # 假设最大可能的汉明距离为64位（对于phash默认设置）
        max_distance = 64
        # 计算单个块的匹配度
        match_degree = 1 - (hamming_distance / max_distance)
        total_match_degree += match_degree

    # 返回所有块的平均匹配度
    return total_match_degree / len(hashes1)

def compute_phash(image, hash_size=16, highfreq_factor=4):
    """
    计算单个图像的感知哈希值。
    :param image: PIL 图像对象
    :param hash_size: 哈希大小
    :param highfreq_factor: 高频因子
    :return: 图像的 pHash 值
    """
    try:
        return phash(image, hash_size=hash_size, highfreq_factor=highfreq_factor)
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def split_image_into_blocks(image, num_blocks):
    """
    将图像分割成指定数量的块。
    :param image: PIL 图像对象
    :param num_blocks: 分割的块数（假设是平方根）
    :return: 块列表
    """
    width, height = image.size
    block_width = width // num_blocks
    block_height = height // num_blocks
    blocks = []
    for i in range(num_blocks):
        for j in range(num_blocks):
            left = j * block_width
            upper = i * block_height
            right = (j + 1) * block_width
            lower = (i + 1) * block_height
            block = image.crop((left, upper, right, lower))
            blocks.append(block)
    return blocks

def compute_block_hashes(image_path, num_blocks, crop_ratio=0.0, preview=0):
    """
    计算图像的分块感知哈希值，支持裁剪和预览。
    :param image_path: 图像文件的路径
    :param num_blocks: 分割的块数（假设是平方根）
    :param crop_ratio: 裁剪比例（0 到 1），表示从顶部裁剪的高度比例
    :param preview: 是否显示裁剪后的图像（1 为显示，0 为不显示）
    :return: 图像的分块 pHash 值列表
    """
    try:
        # 使用 PIL 打开图像
        img = Image.open(image_path)
        
        # 如果 crop_ratio > 0，进行裁剪
        if crop_ratio > 0:
            width, height = img.size
            crop_height = int(height * crop_ratio)
            img = img.crop((0, 0, width, crop_height))  # 裁剪顶部部分
        
        # 当 preview=1 时，显示裁剪后的图像并适配分辨率
        if preview == 1:
            # 设置屏幕分辨率（可根据实际情况调整）
            screen_width, screen_height = 1920, 1080
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            img_height, img_width = img_cv.shape[:2]
            
            # 如果图像过大，进行缩放
            if img_width > screen_width or img_height > screen_height:
                scale = min(screen_width / img_width, screen_height / img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                img_cv = cv2.resize(img_cv, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # 显示图像
            cv2.imshow('Cropped Image', img_cv)
            cv2.waitKey(0)  # 等待按键关闭窗口
            cv2.destroyAllWindows()
        
        # 分割图像成块
        blocks = split_image_into_blocks(img, num_blocks)
        
        # 计算每个块的 pHash 值
        block_hashes = [compute_phash(block) for block in blocks]
        return block_hashes
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return []

def batch_compute_block_hashes(folder_path, num_blocks, crop_ratio=0.0, preview=0):
    """
    批量计算文件夹中所有 JPG 图像的分块 pHash 值，支持裁剪和预览。
    :param folder_path: 包含截图的文件夹路径
    :param num_blocks: 分割的块数（假设是平方根）
    :param crop_ratio: 裁剪比例（0 到 1），表示从顶部裁剪的高度比例
    :param preview: 是否显示裁剪后的图像（1 为显示，0 为不显示）
    :return: 字典，键为文件名，值为对应的分块 pHash 值列表
    """
    hash_dict = {}
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.jpg'):
            img_path = os.path.join(folder_path, filename)
            block_hashes = compute_block_hashes(img_path, num_blocks, crop_ratio, preview)
            if block_hashes:
                hash_dict[filename] = block_hashes
    return hash_dict

def compare_block_hashes(hashes1, hashes2):
    """
    比较两个分块哈希值列表的匹配度。
    :param hashes1: 第一个图像的分块 pHash 值列表
    :param hashes2: 第二个图像的分块 pHash 值列表
    :return: 综合匹配度（0 到 1 之间的浮点数，1 表示完全匹配）
    """
    if len(hashes1) != len(hashes2):
        return 0.0
    
    total_match_degree = 0.0
    for hash1, hash2 in zip(hashes1, hashes2):
        hamming_distance = hash1 - hash2
        max_distance = 64
        match_degree = 1 - (hamming_distance / max_distance)
        total_match_degree += match_degree
    
    return total_match_degree / len(hashes1)

def are_same_image(block_hashes1, block_hashes2, threshold=0.9):
    """
    计算两个图像的相似度。
    :param block_hashes1: 第一个图像的分块 pHash 值列表
    :param block_hashes2: 第二个图像的分块 pHash 值列表
    :param threshold: 匹配度的阈值（0 到 1，默认 0.9）
    :return: 是否相似（布尔值）
    """
    match_degree = compare_block_hashes(block_hashes1, block_hashes2)
    return match_degree >= threshold

def find_duplicates(hash_dict, threshold=0.9):
    """
    遍历所有图像对，计算匹配度并打印相似度高于阈值的图像对。
    :param hash_dict: 图像文件名和分块 pHash 值列表的字典
    :param threshold: 匹配度的阈值（0 到 1，默认 0.9）
    """
    filenames = list(hash_dict.keys())  # 获取所有文件名
    found_similar = False

    # 遍历每张图像与其他图像进行对比
    for i in range(len(filenames)):
        for j in range(i + 1, len(filenames)):  # 从 i+1 开始，避免重复对比和自对比
            file1 = filenames[i]
            file2 = filenames[j]
            block_hashes1 = hash_dict[file1]
            block_hashes2 = hash_dict[file2]
            
            # 计算匹配度
            if are_same_image(block_hashes1, block_hashes2, threshold):
                print(f"{file1} 和 {file2} 的匹配度: {compare_block_hashes(block_hashes1, block_hashes2):.4f}")
                found_similar = True

    if not found_similar:
        print("没有找到相似度高于阈值的图像对。")

if __name__ == "__main__":
    from time import time
    """ 
    # 匹配整个文件使用方法
    # 指定截图文件夹路径
    screenshot_folder = r''  # 替换为实际路径
    num_blocks = 10  # 指定分块的数量（例如 4 表示 2x2 分块）

    start_time = time()
    hash_dict = batch_compute_block_hashes(screenshot_folder, num_blocks, 0.05, 0)
    print("加载图像时间:", time()-start_time)

    start_time = time()
    # 查找并打印重复的图像对
    find_duplicates(hash_dict, threshold=0.66)
    print("搜索时间", time()-start_time)
    start_time = time()
    print("对比时间", time()-start_time)
    """
    start_time = time()
    # 单个文件匹配使用方法
    block_hashes1 = get_image_block_hashes('image_test/1.jpg')
    block_hashes2 = get_image_block_hashes('image_test/7.jpg')
    print("读耗时:", time()-start_time)
    start_time = time()
    block_hashes1 = get_image_block_hashes_optimized('image_test/1.jpg')
    block_hashes2 = get_image_block_hashes_optimized('image_test/7.jpg')
    print("读耗时:", time()-start_time)
    start_time = time()
    match_degree = calculate_match_degree(block_hashes1, block_hashes2)
    print(f"匹配: {match_degree:.4f}")
    print("匹配耗时:", time()-start_time)

