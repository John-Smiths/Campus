import os
from PIL import Image, ImageDraw, ImageFont
from datetime import date

def write_filename_to_image(image_path, class_name, _id):
    print(image_path)
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    today = date.today() # 今天的日期
    formatted_date = f"{today.month}.{today.day}" # 重新定义格式
    
    # 获取文件名，不包括扩展名
    filename_without_ext = os.path.splitext(os.path.basename(image_path))[0]
    
    # 设置字体样式和大小
    try:
        # 增大字体大小
        font_size = 80  # 增大字体大小
        font = ImageFont.truetype("simkai.ttf", font_size)  # 可以尝试使用其他字体
    except IOError:
        font = ImageFont.load_default()  # 如果失败，使用默认字体
    
    # 准备要写入的文本
    text_lines = [f"第{_id}", f"{filename_without_ext}+{formatted_date}", class_name]
    
    # 计算文本的位置，使其居中显示
    max_text_width = 0
    total_text_height = 0
    for line in text_lines:
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        max_text_width = max(max_text_width, text_width)
        total_text_height += text_height
    
    img_width, img_height = img.size
    x = (img_width - max_text_width) // 2  # 文本水平居中
    y = 300  # 从顶部留出一些空间
    
    # 写入文件名到图片上
    current_y = y
    for line in text_lines:
        draw.text((x, current_y), line, fill="red", font=font)
        current_y += text_bbox[3] - text_bbox[1]  # 更新y坐标以写入下一行

    current_y = (img_height - total_text_height) // 2
    for line in text_lines:
        draw.text((x, current_y), line, fill="yellow", font=font)
        current_y += text_bbox[3] - text_bbox[1]  # 更新y坐标以写入下一行
    current_y = 1500 
    for line in text_lines:
        draw.text((x, current_y), line, fill="blue", font=font)
        current_y += text_bbox[3] - text_bbox[1]  # 更新y坐标以写入下一行
      
    # 保存修改后的图片
    if image_path.lower().endswith(('.jpg', '.jpeg')):
        img = img.convert('RGB')  # 强制转为 RGB
    img.save(image_path)

def process_images_in_directory(directory, class_name):
    # 遍历指定目录中的所有文件
    _id = 1
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg')):
            file_path = os.path.join(directory, filename)
            print(f"Processing {file_path}")
            write_filename_to_image(file_path, class_name, str(_id))
            _id += 1

if __name__ == "__main__":
    file_path = input("请输入路径:").strip()
    class_name = input("请输入班级名称:").strip()
    # 调用函数，传入当前工作目录
    process_images_in_directory(file_path, class_name)

