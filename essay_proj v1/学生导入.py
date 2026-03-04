import pandas as pd
from app import app, db, User
from werkzeug.security import generate_password_hash


def batch_import_students(file_path, start_sid = 240101):
    """
    file_path: Excel文件路径
    start_sid: 起始学号（自动对齐递增）
    """
    with app.app_context():
        # 读取Excel，跳过第一行（班级信息）
        try:
            df = pd.read_excel(file_path, skiprows=1, header=None)
        except Exception as e:
            print(f"读取失败: {e}")
            return

        count = 0
        for index, row in df.iterrows():
            student_name = str(row[0]).strip()
            if not student_name or student_name == 'nan':
                continue
            student_id = str(start_sid + count)
            existing_user = User.query.filter_by(username=student_id).first()
            if not existing_user:
                # 默认密码设为学号
                new_student = User(
                    username=student_id,
                    password=generate_password_hash(student_id),
                    role='student'
                )
                db.session.add(new_student)
                print(f"成功导入: {student_name} (学号/账号: {student_id})")
                count += 1
            else:
                print(f"跳过已存在学号: {student_id}")

        db.session.commit()
        print(f"\n--- 导入完成，共计新增 {count} 名学生 ---")


if __name__ == "__main__":
    ssid01 = f"{input("输入学生入校的年份（格式为YY，如2025届高一输入 25 即可）\n")}{input("输入学生班级（格式为0x，如一班输入 01 即可）\n")}01"
    excel_file = f"{input("输入你的excel文件名（不要加扩展名.xlsx）")}.xlsx"
    import os

    if os.path.exists(excel_file):
        batch_import_students(excel_file, int(ssid01))
    else:
        print(f"错误：找不到文件 {excel_file}，请确保它在当前文件夹下")
