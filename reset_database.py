"""
Database Reset Tool for Amdox AI Task Optimizer
"""

import os
import sqlite3

def reset_database():
    """Reset the database by deleting and recreating it"""
    
    db_file = 'amdox.db'
    
    if os.path.exists(db_file):
        print(f"⚠️  Found existing database: {db_file}")
        confirm = input("Are you sure you want to DELETE all data? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ Database reset cancelled.")
            return
        
        os.remove(db_file)
        print(f"✅ Deleted old database: {db_file}")
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE mood_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  employee_id TEXT NOT NULL,
                  emotion TEXT NOT NULL,
                  burnout_score INTEGER NOT NULL,
                  recommended_task TEXT NOT NULL,
                  input_type TEXT DEFAULT 'text',
                  confidence REAL DEFAULT 0.85,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE employees
                 (id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  department TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE media_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  employee_id TEXT NOT NULL,
                  media_type TEXT NOT NULL,
                  file_path TEXT NOT NULL,
                  emotion TEXT NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created new database: {db_file}")
    print("✅ All tables created successfully!")
    print("\n🚀 You can now run: python app.py")

if __name__ == '__main__':
    print("=" * 60)
    print("🔄 Amdox Database Reset Tool")
    print("=" * 60)
    print()
    
    reset_database()