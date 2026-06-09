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


def get_connection():
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )


def init_db():
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
                due_date DATE
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


init_db()


@app.route("/")
def home():

    search = request.args.get("search", "")
    priority_filter = request.args.get("priority", "All")

    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id,
               task,
               completed,
               priority,
               due_date
        FROM tasks
        WHERE 1=1
    """

    params = []

    if search:
        query += " AND task LIKE %s "
        params.append(f"%{search}%")

    if priority_filter != "All":
        query += " AND priority = %s "
        params.append(priority_filter)

    query += """
        ORDER BY
            completed ASC,

            CASE
                WHEN completed = FALSE
                AND due_date IS NOT NULL
                AND due_date < CURDATE()
                THEN 0
                ELSE 1
            END,

            CASE priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
            END,

            due_date ASC
    """

    cur.execute(query, params)
    tasks = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE completed = TRUE
    """)
    completed_tasks = cur.fetchone()[0]

    pending_tasks = total_tasks - completed_tasks

    cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE completed = FALSE
        AND due_date IS NOT NULL
        AND due_date < CURDATE()
    """)
    overdue_tasks = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template(
        "index.html",
        tasks=tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        overdue_tasks=overdue_tasks,
        today=date.today(),
        search=search,
        priority_filter=priority_filter
    )


@app.route("/add", methods=["POST"])
def add():

    task = request.form["task"]
    priority = request.form["priority"]
    due_date = request.form["due_date"] or None

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tasks(task, priority, due_date)
        VALUES(%s, %s, %s)
    """, (task, priority, due_date))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/toggle/<int:id>")
def toggle(id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE tasks
        SET completed = NOT completed
        WHERE id=%s
    """, (id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/delete/<int:id>")
def delete(id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM tasks
        WHERE id=%s
    """, (id,))

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
        due_date = request.form["due_date"] or None

        cur.execute("""
            UPDATE tasks
            SET task=%s,
                priority=%s,
                due_date=%s
            WHERE id=%s
        """, (
            task,
            priority,
            due_date,
            id
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/")

    cur.execute("""
        SELECT id,
               task,
               completed,
               priority,
               due_date
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
    app.run(host="0.0.0.0", port=5000)