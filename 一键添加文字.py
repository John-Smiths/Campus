import os
import sys
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# 字体文件路径（与脚本同目录或指定绝对路径）
FONT_PATH = "simkai.ttf"
# 默认字体大小（可根据图片高度自动缩放）
BASE_FONT_SIZE = 80
# 支持的文件扩展名
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

def parse_filename(filename):
    """
    从文件名解析学号、姓名、班级
    文件名格式：学号-姓名-班级.扩展名
    """
    base = os.path.splitext(filename)[0]
    parts = base.split('-')
    if len(parts) == 3:
        student_id, name, class_name = parts
    else:
        # 如果多于3段，假设第一段是学号，最后一段是班级，中间合并为姓名
        student_id = parts[0]
        class_name = parts[-1]
        name = '-'.join(parts[1:-1])
    return student_id, name, class_name

def get_font(img_height, base_size=BASE_FONT_SIZE):
    """
    根据图片高度动态调整字体大小，确保文字不会溢出
    """
    try:
        font = ImageFont.truetype(FONT_PATH, base_size)
    except IOError:
        print(f"警告：无法加载字体 {FONT_PATH}，使用默认字体")
        font = ImageFont.load_default()
    return font

def add_text_to_image(image_path):
    """
    在图片上添加三组文字（上红、中黄、下蓝）
    """
    try:
        img = Image.open(image_path)
        # 转换为RGB（防止JPEG保存出错）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        draw = ImageDraw.Draw(img)
        img_width, img_height = img.size

        # 解析文件名
        filename = os.path.basename(image_path)
        student_id, name, class_name = parse_filename(filename)

        # 获取当前时间
        now = datetime.now()
        time_str = now.strftime("%Y年%m月%d日%H时")

        # 构建四行文本
        lines = [
            f"学号：{student_id}",
            f"姓名：{name}",
            f"班级：{class_name}",
            f"时间：{time_str}"
        ]

        # 获取字体（动态调整大小防止溢出）
        font = get_font(img_height)
        # 计算每行文本的尺寸
        line_heights = []
        line_widths = []
        total_height = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            line_widths.append(w)
            line_heights.append(h)
            total_height += h

        # 如果总高度超过图片高度，按比例缩小字体
        if total_height > img_height * 0.8:
            # 缩小到原高度的0.7倍
            smaller_size = int(BASE_FONT_SIZE * 0.7)
            font = get_font(img_height, smaller_size)
            # 重新计算
            line_heights = []
            line_widths = []
            total_height = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                line_widths.append(w)
                line_heights.append(h)
                total_height += h

        # 定义三个位置的起始y坐标（上、中、下）
        margin_top = int(img_height * 0.1)  # 距顶部10%
        margin_bottom = int(img_height * 0.1)  # 距底部10%
        center_y = (img_height - total_height) // 2  # 垂直居中

        # 颜色列表
        colors = ['red', 'yellow', 'blue']
        y_positions = [
            margin_top,                # 上
            center_y,                  # 中
            img_height - margin_bottom - total_height  # 下
        ]

        # 分别绘制三组文字
        for color, start_y in zip(colors, y_positions):
            current_y = start_y
            for i, line in enumerate(lines):
                # 水平居中
                x = (img_width - line_widths[i]) // 2
                draw.text((x, current_y), line, fill=color, font=font)
                current_y += line_heights[i]

        # 保存图片（覆盖原文件）
        img.save(image_path)
        print(f"已处理：{image_path}")

    except Exception as e:
        print(f"处理文件 {image_path} 时出错：{e}")

def process_directory(root_dir):
    """
    递归遍历目录，处理所有图片文件
    """
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(IMAGE_EXTENSIONS):
                file_path = os.path.join(root, file)
                add_text_to_image(file_path)

if __name__ == "__main__":
    # 设置工作目录为脚本所在目录（假设字体文件也在该目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 要处理的根目录（相对于当前工作目录）
    base_dirs = [
        os.path.join("db", "学院"),
        os.path.join("db", "群")
    ]

    for base in base_dirs:
        if os.path.exists(base):
            print(f"正在处理目录：{base}")
            process_directory(base)
        else:
            print(f"目录不存在，跳过：{base}")

    print("所有图片处理完成！")