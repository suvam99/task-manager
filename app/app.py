from flask import Flask, jsonify
from db import get_connection
from flask import request


app = Flask(__name__)


@app.route("/", methods=["GET"])
def task_manager():
    return '<h1>Welcome to Task Manager</h1><p>Check out the source code here: <a href="https://github.com/suvam99/task-manager" target="_blank">GitHub Repository</a></p>'


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
    user_id = request.args.get("user_id")

    conn = get_connection()
    if not conn:
        return {"error": "Database not connected"}, 500
    cursor = conn.cursor()
    try:
        if user_id:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return {"error": "No user found"},404
            cursor.execute(
                "SELECT id, title, description, status FROM tasks WHERE user_id = %s;",
                (user_id,),
            )
        else:
            cursor.execute("SELECT * FROM tasks;")
        rows = cursor.fetchall()
        if not rows:
            return [], 200
    except Exception:
        return {"error": "Failed to fetch tasks"}, 500
    finally:
        cursor.close()
        conn.close()

    tasks = []
    for row in rows:
        tasks.append(
            {"id": row[0], "title": row[1], "description": row[2], "status": row[3]}
        )

    return tasks, 200


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()

    title = data.get("title")
    description = data.get("description")
    user_id = data.get("user_id")

    if not title:
        return {"error": "Title is required"}, 400

    if not user_id:
        return {"error": "User ID is required"}, 400

    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE id = %s", [user_id])
        if not cursor.fetchone():
            return {"error": "User not found", "user_id": user_id}, 404

        cursor.execute(
            "INSERT INTO tasks (title, description,user_id) VALUES (%s, %s, %s) RETURNING id;",
            (title, description, user_id),
        )
        task_id = cursor.fetchone()[0]
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"error": "Failed to create task"}, 500
    finally:
        cursor.close()
        conn.close()

    return {"message": "Task created", "id": task_id}, 201


@app.route("/tasks/<int:id>", methods=["PUT"])
def update_task(id):
    data = request.get_json()
    if not data:
        return {"error": "Invalid JSON"}, 400

    user_id = data.get("user_id")
    if not user_id:
        return {"error": "User ID is required"}, 400

    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE tasks
            SET
                title = COALESCE(%s, title),
                description = COALESCE(%s, description),
                status = COALESCE(%s, status)
            WHERE id = %s AND user_id = %s
            RETURNING id, title, description, status
            """,
            (
                data.get("title"),
                data.get("description"),
                data.get("status"),
                id,
                user_id,
            ),
        )

        updated = cursor.fetchone()

        if not updated:
            return {"error": "Task not found"}, 404

        conn.commit()

        result = {
            "id": updated[0],
            "title": updated[1],
            "description": updated[2],
            "status": updated[3],
        }

        return {"message": "Task updated", "updated_to": result}, 200

    except Exception:
        conn.rollback()
        return {"error": "Failed to update task"}, 500

    finally:
        cursor.close()
        conn.close()


@app.route("/tasks/<int:id>", methods=["DELETE"])
def delete_task(id):
    user_id = request.args.get("user_id")
    if not user_id:
        return {"error": "User ID is required"}, 400

    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM tasks WHERE id = %s AND user_id = %s RETURNING id",
            (id, user_id),
        )

        deleted = cursor.fetchone()

        if not deleted:
            return {"error": "Task not found"}, 404

        conn.commit()
        return {"message": "Task deleted", "id": deleted[0]}, 200

    except Exception:
        conn.rollback()
        return {"error": "Failed to delete task"}, 500

    finally:
        cursor.close()
        conn.close()


@app.route("/users", methods=["POST"])
def create_users():
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return {"error": "All fields are required"}, 400

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (username, email, password),
        )
        user_id = cursor.fetchone()[0]
        conn.commit()

    except Exception as e:
        conn.rollback()
        return {"error": "Username or email already exists"}, 400

    finally:
        cursor.close()
        conn.close()

    return {"id": user_id, "username": username}, 201


if __name__ == "__main__":
    app.run(debug=True)
