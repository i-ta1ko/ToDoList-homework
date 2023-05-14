
from flask import Flask, flash, render_template, request, redirect, url_for, session, g, send_from_directory
import sqlite3

app = Flask(__name__)
app.secret_key = 'kahsfhkj3hk24hhk235asd324jasdjgjfdh'
app.config['SESSION_TYPE'] = 'filesystem'


#connect to database
def get_connection():
    conn = sqlite3.connect("todo.db")
    return conn
    
#check if user is logged in
def check_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        db = get_connection()
        g.user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

 #it shows how many projects user have       
def get_project_count():
    db = get_connection()
    project_count = db.execute('SELECT COUNT(*) FROM projects WHERE user_id = ?', (g.user[0],)).fetchone()[0]
    return project_count

#shows how many tasks user have
def get_task_count(project_id):
    db = get_connection()
    task_count = db.execute('SELECT COUNT(*) FROM tasks WHERE project_id = ?', (project_id,)).fetchone()[0]
    return task_count        

#logout      
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

#database
def create_tables():
    db = get_connection()  
    db.execute("""
        CREATE TABLE IF NOT EXISTS users
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT,
        status TEXT)
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS projects
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id))
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS tasks
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        project_id INTEGER,
        completed INTEGER,
        user_id INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (user_id) REFERENCES users (id))
    """)
create_tables()
    
@app.route("/")
def home():
    check_user()
    return render_template('index.html', user=g.user)

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_connection()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()


        if user is None:
            error = "User does not exist"
        elif password != user[2]:
            error = "Wrong password!"
        else:
            session.clear()
            session['user_id'] = user[0]
            if user[3] == 'admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('profile'))
        print("Login failed!")

    return render_template('auth/login.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        error = None

        if password != confirm_password:
            error = "Passwords do not match" 
        else:
            db = get_connection()
            user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()

            if user is not None:
                error = "Username already exists"
            else:
                db.execute('INSERT INTO users(username, password, role, status) VALUES (?, ?, ?, ?)', (username, password, 'free', 'active')) 
                db.commit()
                return redirect(url_for('login'))
        
        print(error)

    return render_template('auth/register.html')

@app.route('/profile')
def profile():
    check_user()
    if g.user is None:
        return redirect(url_for('login'))
    return render_template('profile.html')

@app.route('/dashboard')
def dashboard():
    check_user()
    if g.user is None or g.user[3] != 'admin':
        return redirect(url_for('login'))
    if g.user[3] == 'admin':
        db = get_connection()
        users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        return render_template('dashboard.html', users=users)
    return redirect(url_for('profile'))

@app.route('/dashboard/upgrade/<int:user_id>', methods=['POST'])
def upgrade_user(user_id):

    db = get_connection()
    db.execute('UPDATE users SET role = "premium" WHERE id = ?', (user_id,))
    db.commit()

    return redirect(url_for('dashboard'))

@app.route('/nonlogged')
def nonlogged():
    return render_template('nonlogged.html')

@app.route('/dashboard/terminate/<int:user_id>', methods=['POST'])
def terminate_user(user_id):

    db = get_connection()
    db.execute('UPDATE users SET status = "terminated" WHERE id = ?', (user_id,))
    db.commit()

    return redirect(url_for('dashboard'))

@app.route('/dashboard/downgrade/<int:user_id>', methods=['POST'])
def downgrade_user(user_id):
    
    db = get_connection()
    db.execute('UPDATE users SET role = "free" WHERE id = ?', (user_id,))
    db.commit()

    return redirect(url_for('dashboard'))

@app.route('/dashboard/activate/<int:user_id>', methods=['POST'])
def activate_user(user_id):

    db = get_connection()
    db.execute('UPDATE users SET status = "active" WHERE id = ?', (user_id,))
    db.commit()

    return redirect(url_for('dashboard'))

@app.route('/create_project', methods=['POST'])
def create_project():
    check_user()

    if g.user is None:
        return redirect(url_for('login'))
    
    if g.user[3] == 'free':
        project_count = get_project_count()
        if project_count >= 5:
            return redirect(url_for('todo'))

    name = request.form['project_name']
    db = get_connection()
    db.execute('INSERT INTO projects (name, user_id) VALUES (?, ?)', (name, g.user[0]))
    db.commit()
    
    return redirect(url_for('todo'))

@app.route('/delete_project/<int:project_id>')
def delete_project(project_id):
    check_user()
    if g.user is None:
        return redirect(url_for('login'))
    db = get_connection()
    db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    db.execute('DELETE FROM tasks WHERE project_id = ?', (project_id,))
    db.commit()

    return redirect(url_for('todo'))

@app.route('/create_task', methods=['POST'])
def create_task():
    check_user()
    if g.user is None:
        return redirect(url_for('login'))
    project_id = int(request.form['project'])
    if g.user[3] == 'free':
        task_count = get_task_count(project_id)
        if task_count >= 15:
            flash("You have reached the maximum number of tasks for this project.")
            return redirect(url_for('todo'))

    name = request.form['task_name']
    db = get_connection()
    db.execute('INSERT INTO tasks (name, project_id, completed, user_id) VALUES (?, ?, ?, ?)', (name, project_id, 0, g.user[0]))
    db.commit()

    return redirect(url_for('todo'))

@app.route('/complete_task/<int:task_id>', methods=['GET'])
def complete_task(task_id):
    check_user()
    db = get_connection()
    db.execute('UPDATE tasks SET completed = 1 WHERE id = ?', (task_id,))
    db.commit()
    return redirect(url_for('todo'))

@app.route('/delete_task/<int:task_id>', methods=['GET'])
def delete_task(task_id):
    check_user()
    db = get_connection()
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('todo'))

@app.route('/todo', methods=['POST', 'GET'])
def todo():
    check_user()

    if g.user is None:
        return redirect(url_for('login'))

    db = get_connection()

    if request.method == 'POST':
        # Create a new project
        if request.form.get('project_name'):
            project_name = request.form['project_name']    
            db.execute('INSERT INTO projects (name, user_id) VALUES (?, ?)', (project_name, g.user[0]))
            db.commit()
    elif request.method == 'GET':

        # Create a new task
        if request.form.get('task_name'):
            task_name = request.form['task_name']
            project_id = request.form['project']   
            db.execute('INSERT INTO tasks (name, project_id, date) VALUES (?, ?, ?)', (task_name, project_id, request.form['date']))
            db.commit()

    # Get all projects and tasks for the current user
    projects = db.execute('SELECT * FROM projects WHERE user_id = ?', (g.user[0],)).fetchall()
    tasks = db.execute('SELECT * FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE user_id = ?)', (g.user[0],)).fetchall()

    return render_template('todo.html', user=g.user, projects=projects, tasks=tasks)

@app.route('/upgrade', methods=['GET'])
def upgrade():
    db = get_connection()
    check_user()
    user_id = g.user[0]
    db.execute('UPDATE users SET role = "premium" WHERE id = ?', (user_id,))
    db.commit()
    flash('Your account has been upgraded to premium!', 'success')
    return redirect(url_for('profile'))

@app.route('/undo_task/<int:task_id>', methods=['GET'])

def undo_task(task_id):
    check_user()
    db = get_connection()
    db.execute('UPDATE tasks SET completed = 0 WHERE id = ?', (task_id,))
    db.commit()
    return redirect(url_for('todo'))

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if request.method == 'POST':
        new_task_name = request.form.get('new_task_name')
        db = get_connection()
        db.execute("UPDATE tasks SET name = ? WHERE id = ?", (new_task_name, task_id))
        db.commit()
        return redirect(url_for('todo'))

@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if request.method == 'POST':
        new_project_name = request.form.get('new_project_name')
        db = get_connection()
        db.execute("UPDATE projects SET name = ? WHERE id = ?", (new_project_name, project_id))
        db.commit()
        return redirect(url_for('todo'))
    
