import sqlite3

def initialize_db():
    # Create or connect to the SQLite database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Create the users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Insert a test user (plain text password)
    #c.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('testuser', 'testpassword'))
    c.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('manjulaketha949055@gmail.com', 'test'))


    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()
