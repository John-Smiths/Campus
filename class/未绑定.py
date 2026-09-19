import json
from pathlib import Path
import pandas as pd

# 当前目录
current_dir = Path.cwd()

# 存储结果的列表，用于生成 Excel
results = []

# 遍历所有 .json 文件
for json_file in current_dir.glob("*.json"):
    # 跳过 Group.json、临时文件（.开头 或 .un~结尾）
    if (json_file.name.lower() == "group.json" or
        json_file.name.startswith(".") or
        json_file.name.endswith(".un~")):
        continue

    class_name = json_file.stem  # 班级名
    print(f"正在检查班级: {class_name}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 收集该班所有未绑定学生
        unbound_students = []
        for student_id, student_info in data.items():
            if not student_info.get("QID", "").strip():
                name = student_info.get("姓名", "未知姓名")
                unbound_students.append((class_name, student_id, name))

        # 判断绑定情况
        if len(unbound_students) == 0:
            # 全部已绑定，跳过
            continue
        elif len(unbound_students) == len(data):
            # 全班未绑定
            print(f"{class_name} -> 全班未绑定")
            results.append({
                "班级": class_name,
                "学号": "全班",
                "姓名": "未绑定",
                "备注": "全班未绑定"
            })
        else:
            # 部分未绑定，逐个输出
            for cls, sid, name in unbound_students:
                print(f"{cls} -> {sid} -> {name} 未绑定")
                results.append({
                    "班级": cls,
                    "学号": sid,
                    "姓名": name,
                    "备注": "个人未绑定"
                })

    except Exception as e:
        print(f"❌ 读取或解析文件 {json_file.name} 时出错: {e}")
        results.append({
            "班级": class_name,
            "学号": "解析错误",
            "姓名": "N/A",
            "备注": f"错误: {e}"
        })

# 输出完成
print("✅ 检查完成。")

# 将结果写入 Excel
if results:
    df = pd.DataFrame(results)
    output_file = current_dir / "未绑定名单.xlsx"
    try:
        df.to_excel(output_file, index=False, sheet_name="未绑定名单")
        print(f"📋 未绑定名单已保存至: {output_file}")
    except Exception as e:
        print(f"❌ 保存 Excel 文件失败: {e}")
else:
    print("🎉 所有学生均已绑定，无需生成名单。")