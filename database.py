import sqlite3
import json
import os

DB_NAME = "workspace_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS projects 
                      (id INTEGER PRIMARY KEY, name TEXT, path TEXT)''')
    try: cursor.execute("ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'active'")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE projects ADD COLUMN details TEXT")
    except sqlite3.OperationalError: pass
    try: cursor.execute("ALTER TABLE projects ADD COLUMN timeline TEXT")
    except sqlite3.OperationalError: pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS folder_info (path TEXT PRIMARY KEY, info TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, status TEXT DEFAULT 'pending', details TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    
    defaults = {
        'subfolders': ["01_CAD_UG_NX", "02_FEA_ANSYS", "03_Scripts", "04_Reports"],
        'project_fields': ["Project Description", "Client Name", "Priority"],
        'dashboard_fields': ["Client Name", "Priority"],
        'main_path': "",
        'user_name': "Engineer"
    }

    for key, val in defaults.items():
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        if not cursor.fetchone():
            value = val if key == 'main_path' else json.dumps(val)
            cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    result = cursor.fetchone()
    conn.close()
    if not result: return ""
    return result[0] if key == 'main_path' else json.loads(result[0])

def update_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if key != 'main_path': value = json.dumps(value)
    cursor.execute("UPDATE OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def add_project(name, main_path, details_dict):
    project_path = os.path.join(main_path, name)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO projects (name, path, status, details) VALUES (?, ?, 'active', ?)", 
                   (name, project_path, json.dumps(details_dict)))
    conn.commit()
    conn.close()
    return project_path

def get_all_projects():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, path, details, status FROM projects")
    projects = cursor.fetchall()
    conn.close()
    return projects

def update_project_details(name, new_status, details_dict):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET status=?, details=? WHERE name=?", 
                   (new_status, json.dumps(details_dict), name))
    conn.commit()
    conn.close()

def get_project_timeline(name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT timeline FROM projects WHERE name=?", (name,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]: return json.loads(result[0])
    return []

def update_project_timeline(name, timeline_list):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET timeline=? WHERE name=?", (json.dumps(timeline_list), name))
    conn.commit()
    conn.close()

def get_folder_info(path):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT info FROM folder_info WHERE path=?", (path,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else ""

def set_folder_info(path, info):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO folder_info (path, info) VALUES (?, ?)", (path, info))
    conn.commit()
    conn.close()

def add_task(date_str, details_dict):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (date, details) VALUES (?, ?)", (date_str, json.dumps(details_dict)))
    conn.commit()
    conn.close()

def get_tasks_by_date(date_str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, details FROM tasks WHERE date=?", (date_str,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_all_tasks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, status, details FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, new_status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
    conn.commit()
    conn.close()

def get_dates_with_tasks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM tasks")
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates