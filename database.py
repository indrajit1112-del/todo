import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Projects Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        ''')
        
        # Insert default inbox project
        cursor.execute("INSERT OR IGNORE INTO projects (name) VALUES ('inbox')")
        
        # Tasks Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            notes TEXT,
            due_date TEXT,
            task_type TEXT,
            completed BOOLEAN DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (parent_id) REFERENCES tasks(id)
        )
        ''')
        
        # Tags Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        ''')
        
        # Task Tags Junction Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_tags (
            task_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (task_id, tag_id),
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        )
        ''')
        
        # Memory Table for OpenAI API feedback
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_text TEXT NOT NULL UNIQUE
        )
        ''')

# --- Project Methods ---
def get_projects():
    with get_db_connection() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM projects').fetchall()]

def add_project(name):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO projects (name) VALUES (?)', (name.strip().lower(),))
        return cursor.lastrowid

# --- Memory Methods ---
def get_memory_rules():
    with get_db_connection() as conn:
        return [row['rule_text'] for row in conn.execute('SELECT rule_text FROM memory').fetchall()]

def add_memory_rule(rule_text):
    with get_db_connection() as conn:
        conn.execute('INSERT OR IGNORE INTO memory (rule_text) VALUES (?)', (rule_text,))

# --- Tag Methods ---
def get_tags():
    with get_db_connection() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM tags').fetchall()]

def get_or_create_tag(name):
    name = name.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (name,))
        cursor.execute('SELECT id FROM tags WHERE name = ?', (name,))
        return cursor.fetchone()['id']

# --- Task Methods ---
def add_task(title, project_id=1, parent_id=None, description="", notes="", due_date=None, task_type=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (project_id, parent_id, title, description, notes, due_date, task_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, parent_id, title, description, notes, due_date, task_type))
        return cursor.lastrowid

def update_task(task_id, **kwargs):
    if not kwargs: return
    
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(task_id)
    
    query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
    with get_db_connection() as conn:
        conn.execute(query, tuple(values))

def delete_task(task_id):
    with get_db_connection() as conn:
        # Delete related task tags
        conn.execute('DELETE FROM task_tags WHERE task_id = ?', (task_id,))
        # Orphan subtasks (unset parent_id)
        conn.execute('UPDATE tasks SET parent_id = NULL WHERE parent_id = ?', (task_id,))
        # Delete task
        conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))

def get_tasks(project_id=None, include_completed=False):
    query = 'SELECT * FROM tasks'
    params = []
    conditions = []
    
    if project_id:
        conditions.append('project_id = ?')
        params.append(project_id)
        
    if not include_completed:
        conditions.append('completed = 0')
        
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
        
    with get_db_connection() as conn:
        tasks = [dict(row) for row in conn.execute(query, tuple(params)).fetchall()]
        
        # Load tags for each task
        for task in tasks:
            tags_query = '''
            SELECT t.name FROM tags t
            JOIN task_tags tt ON t.id = tt.tag_id
            WHERE tt.task_id = ?
            '''
            task['tags'] = [r['name'] for r in conn.execute(tags_query, (task['id'],)).fetchall()]
            
        return tasks

def add_tag_to_task(task_id, tag_name):
    tag_id = get_or_create_tag(tag_name)
    with get_db_connection() as conn:
        conn.execute('INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)', (task_id, tag_id))

def clear_task_tags(task_id):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM task_tags WHERE task_id = ?', (task_id,))

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
