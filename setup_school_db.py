import sqlite3
import random
from datetime import datetime

def init_school_db():
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()

    # 1. 建立資料表 (Schema Design)
    # 學生表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            enrollment_year INTEGER,
            major TEXT
        )
    ''')

    # 教師表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT,
            title TEXT -- e.g. Professor, Associate Professor
        )
    ''')

    # 課程表 (連結到教師)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            course_id INTEGER PRIMARY KEY,
            course_name TEXT NOT NULL,
            credits INTEGER,
            teacher_id INTEGER,
            FOREIGN KEY(teacher_id) REFERENCES teachers(teacher_id)
        )
    ''')

    # 選課與成績表 (這是多對多關聯的核心，最常需要 JOIN 的地方)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            enrollment_id INTEGER PRIMARY KEY,
            student_id INTEGER,
            course_id INTEGER,
            grade INTEGER, -- 0-100 分
            semester TEXT, -- e.g. '2023-Fall'
            FOREIGN KEY(student_id) REFERENCES students(student_id),
            FOREIGN KEY(course_id) REFERENCES courses(course_id)
        )
    ''')

    # 2. 生成一些假資料 (Mock Data Generation)
    print("正在生成假資料...")
    
    # 塞入教師
    departments = ['CS', 'Math', 'Physics', 'History']
    cursor.executemany('INSERT INTO teachers (name, department, title) VALUES (?, ?, ?)', [
        ('Dr. Alan Turing', 'CS', 'Professor'),
        ('Dr. Richard Feynman', 'Physics', 'Professor'),
        ('Dr. John Nash', 'Math', 'Associate Professor'),
        ('Dr. Grace Hopper', 'CS', 'Professor')
    ])

    # 塞入課程
    cursor.executemany('INSERT INTO courses (course_name, credits, teacher_id) VALUES (?, ?, ?)', [
        ('Algorithms', 3, 1),
        ('Quantum Mechanics', 4, 2),
        ('Game Theory', 3, 3),
        ('Operating Systems', 4, 4),
        ('Calculus I', 3, 3)
    ])

    # 塞入學生 (隨機生成 10 位)
    students_data = []
    first_names = ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Heidi', 'Ivan', 'Judy']
    majors = ['CS', 'Physics', 'Math']
    
    for i in range(10):
        name = f"{first_names[i]} Doe"
        email = f"{first_names[i].lower()}@school.edu"
        students_data.append((name, email, 2023, random.choice(majors)))
    
    cursor.executemany('INSERT INTO students (name, email, enrollment_year, major) VALUES (?, ?, ?, ?)', students_data)

    # 塞入選課紀錄 (每位學生隨機選 2-3 門課，並隨機打分數)
    enrollments_data = []
    for student_id in range(1, 11): # 假設 ID 從 1 到 10
        selected_courses = random.sample(range(1, 6), k=random.randint(2, 3))
        for course_id in selected_courses:
            grade = random.randint(50, 100) # 分數在 50 到 100 之間
            enrollments_data.append((student_id, course_id, grade, '2023-Fall'))
            
    cursor.executemany('INSERT INTO enrollments (student_id, course_id, grade, semester) VALUES (?, ?, ?, ?)', enrollments_data)

    conn.commit()
    conn.close()
    print("資料庫 school.db 建置完成！")

if __name__ == '__main__':
    init_school_db()