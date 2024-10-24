import os
from PIL import Image, ImageDraw, ImageFont

def write_filename_to_image(image_path, class_name):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    filename_without_ext = os.path.splitext(os.path.basename(image_path))[0]

    try:

        font_size = 80 
        font = ImageFont.truetype("simkai.ttf", font_size) 
    except IOError:
        font = ImageFont.load_default()  

    text_lines = [filename_without_ext, class_name]

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
    y = 650  
    current_y = y
    for line in text_lines:
        draw.text((x, current_y), line, fill="black", font=font)
        current_y += text_bbox[3] - text_bbox[1] 

    img.save(image_path)

def process_images_in_directory(directory, class_name):

    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg')):
            file_path = os.path.join(directory, filename)
            print(f"Processing {file_path}")
            write_filename_to_image(file_path, class_name)

if __name__ == "__main__":
    file_path = input("请输入路径:").strip()
    class_name = input("请输入班级名称:").strip()

    process_images_in_directory(file_path, class_name)
