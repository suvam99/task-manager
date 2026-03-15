import bcrypt
from flask import Blueprint, request

from auth import verify_password, generate_token, verify_token
from db import get_connection

bp = Blueprint("main", __name__)


@bp.route("/", methods=["GET"])
def task_manager():
    return '<h1>Welcome to Task Manager</h1><p>Check out the source code here: <a href="https://github.com/suvam99/task-manager" target="_blank">GitHub Repository</a></p>'


@bp.route("/health", methods=["GET"])
def health():
    conn = get_connection()
    if conn:
        conn.close()
        return {"status": "ok", "db": "connected"}, 200
    else:
        return {"status": "error", "db": "not connected"}, 500


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return {"error": "Invalid JSON"}, 400

    identifier = data.get("user")
    password = data.get("password")

    if not identifier or not password:
        return {"error": "Identifier and password required"}, 400

    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, password_hash FROM users WHERE username = %s OR email = %s",
            (identifier, identifier),
        )

        row = cursor.fetchone()

        if not row:
            return {"error": "Invalid credentials"}, 401

        user_id, stored_hash = row

        if not verify_password(password, stored_hash):
            return {"error": "Invalid credentials"}, 401

        token = generate_token(user_id)

        return {"message": "Login successful", "access_token": token}, 200

    finally:
        cursor.close()
        conn.close()


@bp.route("/tasks", methods=["GET"])
def get_tasks():
    user_id, error, status = verify_token()

    if error:
        return error, status

    conn = get_connection()
    if not conn:
        return {"error": "Database not connected"}, 500
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, title, description, status FROM tasks WHERE user_id = %s;",
            (user_id,),
        )
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


@bp.route("/tasks", methods=["POST"])
def create_task():
    user_id, error, status = verify_token()

    if error:
        return error, status
    data = request.get_json()

    title = data.get("title")
    description = data.get("description")

    if not title:
        return {"error": "Title is required"}, 400

    if not user_id:
        return {"error": "User ID is required"}, 400

    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed"}, 500

    cursor = conn.cursor()
    try:
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


@bp.route("/tasks/<int:id>", methods=["PUT"])
def update_task(id):
    user_id, error, status = verify_token()

    if error:
        return error, status

    data = request.get_json()
    if not data:
        return {"error": "Invalid JSON"}, 400

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


@bp.route("/tasks/<int:id>", methods=["DELETE"])
def delete_task(id):
    user_id, error, status = verify_token()

    if error:
        return error, status

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


@bp.route("/users", methods=["POST"])
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

    hassed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (username, email, hassed_password.decode("utf-8")),
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
