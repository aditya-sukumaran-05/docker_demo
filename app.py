from flask import Flask, render_template, request, redirect
import mysql.connector
import time
import os
from datetime import date

app = Flask(__name__)

host = os.getenv("MYSQL_HOST")
user = os.getenv("MYSQL_USER")
password = os.getenv("MYSQL_PASSWORD")
database = os.getenv("MYSQL_DATABASE")
port = int(os.getenv("MYSQL_PORT", 3306))

def get_connection():
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port
    )


def init_db():
    try:
        while True:
            try:
                conn = get_connection()
                cur = conn.cursor()
    
                cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks(
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    task VARCHAR(255),
                    completed BOOLEAN DEFAULT FALSE,
                    priority VARCHAR(10) DEFAULT 'Medium',
                    category VARCHAR(50) DEFAULT 'General',
                    notes TEXT,
                    due_date DATE,
                    status VARCHAR(20) DEFAULT 'To Do',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
    
                conn.commit()
    
                cur.close()
                conn.close()
    
                print("Database ready")
                break
    
            except Exception as e:
                print("Waiting for MySQL...", e)
                time.sleep(5)
    except Exception as e:
        print(e)
@app.route("/ping")
def ping():
    return "pong"
init_db()

@app.route("/health")
def health():
    return {
        "status": "healthy"
    }
@app.route("/dbtest")
def dbtest():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return f"Database Connected: {result}"
    except Exception as e:
        return f"Database Error: {str(e)}"
@app.route("/")
def home():

    search = request.args.get("search", "")
    priority_filter = request.args.get("priority", "All")
    category_filter = request.args.get("category", "All")
    sort_by = request.args.get("sort", "priority")

    try:

        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                id,
                task,
                completed,
                priority,
                category,
                notes,
                due_date,
                status,
                created_at
            FROM tasks
            WHERE 1=1
        """

        params = []

        if search:
            query += " AND task LIKE %s "
            params.append(f"%{search}%")

        if priority_filter != "All":
            query += " AND priority=%s "
            params.append(priority_filter)

        if category_filter != "All":
            query += " AND category=%s "
            params.append(category_filter)

        if sort_by == "priority":

            query += """
            ORDER BY

            CASE status
                WHEN 'To Do' THEN 1
                WHEN 'In Progress' THEN 2
                WHEN 'Blocked' THEN 3
                WHEN 'Completed' THEN 4
            END,

            CASE priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
            END,

            due_date ASC
            """

        elif sort_by == "due_date":

            query += """
            ORDER BY due_date ASC
            """

        elif sort_by == "category":

            query += """
            ORDER BY category ASC,
                     due_date ASC
            """

        elif sort_by == "newest":

            query += """
            ORDER BY created_at DESC
            """

        elif sort_by == "oldest":

            query += """
            ORDER BY created_at ASC
            """

        elif sort_by == "status":

            query += """
            ORDER BY

            CASE status
                WHEN 'To Do' THEN 1
                WHEN 'In Progress' THEN 2
                WHEN 'Blocked' THEN 3
                WHEN 'Completed' THEN 4
            END
            """

        cur.execute(query, params)
        tasks = cur.fetchall()

        # ======================
        # Dashboard Analytics
        # ======================

        cur.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = cur.fetchone()[0]

        cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE status='To Do'
        """)
        todo_tasks = cur.fetchone()[0]

        cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE status='In Progress'
        """)
        progress_tasks = cur.fetchone()[0]

        cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE status='Blocked'
        """)
        blocked_tasks = cur.fetchone()[0]

        cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE status='Completed'
        """)
        completed_tasks = cur.fetchone()[0]

        cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE priority='High'
        """)
        high_priority_tasks = cur.fetchone()[0]

        cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE status!='Completed'
        AND due_date IS NOT NULL
        AND due_date < CURDATE()
        """)
        overdue_tasks = cur.fetchone()[0]

        completion_percentage = 0

        if total_tasks > 0:
            completion_percentage = round(
                (completed_tasks / total_tasks) * 100
            )

        cur.close()
        conn.close()

        return render_template(
            "index.html",
            tasks=tasks,
            total_tasks=total_tasks,
            todo_tasks=todo_tasks,
            progress_tasks=progress_tasks,
            blocked_tasks=blocked_tasks,
            completed_tasks=completed_tasks,
            overdue_tasks=overdue_tasks,
            high_priority_tasks=high_priority_tasks,
            completion_percentage=completion_percentage,
            today=date.today(),
            search=search,
            priority_filter=priority_filter,
            category_filter=category_filter,
            sort_by=sort_by
        )

    except Exception as e:

        print("Database unavailable:", e)

        return render_template(
            "index.html",
            tasks=[],
            total_tasks=0,
            todo_tasks=0,
            progress_tasks=0,
            blocked_tasks=0,
            completed_tasks=0,
            overdue_tasks=0,
            high_priority_tasks=0,
            completion_percentage=0,
            today=date.today(),
            search=search,
            priority_filter=priority_filter,
            category_filter=category_filter,
            sort_by=sort_by
        )
    
@app.route("/add", methods=["POST"])
def add():

    task = request.form["task"]
    priority = request.form["priority"]
    category = request.form["category"]
    notes = request.form["notes"]
    due_date = request.form["due_date"] or None

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO tasks(
        task,
        priority,
        category,
        notes,
        due_date,
        status
    )
    VALUES(%s,%s,%s,%s,%s,'To Do')
    """, (
        task,
        priority,
        category,
        notes,
        due_date
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/status/<int:id>/<new_status>")
def update_status(id, new_status):

    allowed = [
        "To Do",
        "In Progress",
        "Blocked",
        "Completed"
    ]

    if new_status not in allowed:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    UPDATE tasks
    SET
        status=%s,
        completed=%s
    WHERE id=%s
    """, (
        new_status,
        new_status == "Completed",
        id
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/delete/<int:id>")
def delete(id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM tasks WHERE id=%s",
        (id,)
    )

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":

        task = request.form["task"]
        priority = request.form["priority"]
        category = request.form["category"]
        notes = request.form["notes"]
        due_date = request.form["due_date"] or None
        status = request.form["status"]

        cur.execute("""
        UPDATE tasks
        SET
            task=%s,
            priority=%s,
            category=%s,
            notes=%s,
            due_date=%s,
            status=%s,
            completed=%s
        WHERE id=%s
        """, (
            task,
            priority,
            category,
            notes,
            due_date,
            status,
            status == "Completed",
            id
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/")

    cur.execute("""
    SELECT
        id,
        task,
        completed,
        priority,
        category,
        notes,
        due_date,
        status,
        created_at
    FROM tasks
    WHERE id=%s
    """, (id,))

    task = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "edit.html",
        task=task
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
