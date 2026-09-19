import os
import pandas as pd
import json
import hashlib

def generate_qid(student_id):
    """
    根据学号生成唯一的QID
    """
    return ""
    # 使用SHA256哈希算法生成固定长度的唯一标识符
    hash_object = hashlib.sha256(student_id.encode('utf-8'))
    hex_dig = hash_object.hexdigest().upper()
    # 取前16位字符作为QID（与示例格式匹配）
    return hex_dig[:16]

def convert_excel_to_json(excel_folder='excel', json_folder='json'):
    """
    读取excel文件夹下的所有Excel文件，并将其转换为指定格式的JSON文件保存到json文件夹下。
    
    Args:
        excel_folder (str): Excel文件所在文件夹，默认为'excel'
        json_folder (str): JSON文件输出文件夹，默认为'json'
    """
    # 确保输出文件夹存在
    os.makedirs(json_folder, exist_ok=True)

    # 遍历Excel文件夹下的所有文件
    for filename in os.listdir(excel_folder):
        if filename.lower().endswith(('.xlsx', '.xls')):
            excel_path = os.path.join(excel_folder, filename)
            
            # 读取Excel文件，假设第一列是姓名，第二列是学号，无标题行
            try:
                # 指定引擎以兼容不同版本
                if filename.lower().endswith('.xlsx'):
                    df = pd.read_excel(excel_path, header=None, engine='openpyxl')
                else:  # .xls文件
                    df = pd.read_excel(excel_path, header=None, engine='xlrd')
            except Exception as e:
                print(f"无法读取文件 {filename}: {e}")
                continue

            # 检查是否有至少两列数据
            if df.shape[1] < 2:
                print(f"文件 {filename} 列数不足，跳过")
                continue

            # 创建学生信息字典
            student_info = {}

            # 遍历每一行数据
            for index, row in df.iterrows():
                name = str(row[0])  # 第一列是姓名
                student_id = str(row[1])  # 第二列是学号

                print(name, student_id)
                
                # 生成QID
                qid = generate_qid(student_id)
                
                # 创建学生信息字典
                student_data = {
                    "学号": student_id,
                    "姓名": name,
                    "密码": student_id,  # 密码就是学号
                    "QID": qid  # 生成的QID
                }
                
                # 使用学号作为键
                student_info[student_id] = student_data

            # 构建最终的JSON结构

            student_info

            # 构建输出JSON文件路径
            base_name = os.path.splitext(filename)[0]
            json_filename = base_name + '.json'
            json_path = os.path.join(json_folder, json_filename)

            # 写入JSON文件
            try:
                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(student_info, json_file, ensure_ascii=False, indent=4)
                print(f"成功将 {filename} 转换为 {json_filename}")
            except Exception as e:
                print(f"写入文件 {json_filename} 时出错: {e}")

if __name__ == "__main__":
    convert_excel_to_json()
