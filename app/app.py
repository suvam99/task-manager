from flask import Flask, jsonify
from db import get_connection
from flask import request


app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    conn = get_connection()
    if conn:
        conn.close()
        return {"status": "ok", "db": "connected"}, 200
    else:
        return {"status": "error", "db": "not connected"}, 500


@app.route("/tasks", methods=["GET"])
def get_tasks():
    conn = get_connection()

    if not conn:
        return {"error": "Database not connected"}, 500

    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, status FROM tasks;")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    tasks = []
    for row in rows:
        tasks.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "status": row[3]
        })

    return tasks, 200

@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()

    title = data.get("title")
    description = data.get("description")

    if not title:
        return {"error": "Title is required"}, 400

    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tasks (title, description) VALUES (%s, %s) RETURNING id;",
        (title, description)
    )

    task_id = cursor.fetchone()[0]

    conn.commit()

    cursor.close()
    conn.close()

    return {"message": "Task created", "id": task_id}, 201



@app.route("/tasks/<int:id>", methods=["PUT"])
def update_task(id):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    data = request.get_json()
    cursor = conn.cursor()
    
    cursor.execute("SELECT title, description, status FROM tasks WHERE id = %s", (id,))
    task = cursor.fetchone()

    if task is None:
        cursor.close()
        conn.close()
        return {"error": "Task not found"}, 404

    title = data.get("title", task[0])
    description = data.get("description", task[1])
    status = data.get("status", task[2])

    cursor.execute(
        """UPDATE tasks SET title = %s, description = %s, status = %s WHERE id = %s 
           RETURNING id, title, description, status""", 
        (title, description, status, id)
    )
    
    updated_row = cursor.fetchone()
    conn.commit()

    res = {
        "id": updated_row[0],
        "title": updated_row[1],
        "description": updated_row[2],
        "status": updated_row[3]
    }

    cursor.close()
    conn.close()

    return {"message": f"Task updated for id {id}", "updated_to": res}, 200

@app.route("/tasks/<int:id>", methods=["DELETE"])
def delete_task(id):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    cursor = conn.cursor()


    cursor.execute("DELETE FROM tasks WHERE id = %s RETURNING id", (id,))
    task = cursor.fetchone()
    if not task:
        cursor.close()
        conn.close()
        return {"error": "task not found"}, 404
    conn.commit()
    
    cursor.close()
    conn.close()

    return {"message": "Task Deleted", "id": id}, 200


if __name__ == "__main__":
    app.run(debug=True)