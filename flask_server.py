"""
Flask Backend for Rehab Games Platform
======================================
This allows streaming Python games to web browser
Run: python flask_server.py
"""

from flask import Flask, render_template, Response, jsonify, request
from flask_cors import CORS
import cv2
import threading
import base64
import importlib.util
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__, 
           static_folder='web_platform',
           template_folder='web_platform')
CORS(app)


@app.after_request
def apply_security_headers(response):
    """Allow same-origin camera access for embedded game pages."""
    response.headers['Permissions-Policy'] = 'camera=(self), microphone=(self)'
    return response

# Global variables for game state
current_game = None
camera_active = False
output_frame = None
frame_lock = threading.Lock()

DB_PATH = Path('progress_data.db')


def get_db_connection():
    """Create SQLite connection with dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def display_name_from_user_id(user_id):
    """Generate a readable fallback display name from user_id."""
    slug = (user_id or '').replace('patient-', '').strip('-')
    if not slug:
        return 'Patient'
    return ' '.join(part.capitalize() for part in slug.split('-') if part)


def init_progress_db():
    """Initialize local progress database."""
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            patient_name TEXT NOT NULL DEFAULT '',
            game_id TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            score INTEGER NOT NULL DEFAULT 0,
            reps INTEGER NOT NULL DEFAULT 0,
            accuracy REAL NOT NULL DEFAULT 0,
            completed_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # Backward-compatible migration for existing DBs created before patient_name.
    cols = [row['name'] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    if 'patient_name' not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN patient_name TEXT NOT NULL DEFAULT ''")

    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Serve the main platform page"""
    return render_template('index.html')

@app.route('/api/games')
def list_games():
    """API endpoint to list available games"""
    games = [
        {
            'id': 'shoulder-rehab',
            'name': 'Shoulder & Posture Rehab',
            'file': 'rehabplay.py',
            'description': 'Pose tracking for rehabilitation'
        },
        {
            'id': 'object-catch',
            'name': 'Pinch & Catch Challenge',
            'file': 'object_catch_game.py',
            'description': 'Hand coordination game'
        },
        {
            'id': 'finger-trainer',
            'name': 'Finger Coordination Trainer',
            'file': '1one.py',
            'description': 'Finger dexterity exercises'
        }
    ]
    return jsonify(games)

@app.route('/api/start_game/<game_id>')
def start_game(game_id):
    """Start a Python game"""
    global current_game, camera_active
    
    game_files = {
        'shoulder-rehab': 'rehabplay.py',
        'object-catch': 'object_catch_game.py',
        'finger-trainer': '1one.py'
    }
    
    if game_id not in game_files:
        return jsonify({'error': 'Game not found'}), 404
    
    try:
        # Load and initialize game
        game_file = game_files[game_id]
        spec = importlib.util.spec_from_file_location("game", game_file)
        game_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(game_module)
        
        current_game = game_module
        camera_active = True
        
        return jsonify({'status': 'started', 'game': game_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_game')
def stop_game():
    """Stop current game"""
    global camera_active
    camera_active = False
    return jsonify({'status': 'stopped'})


@app.route('/api/progress/session', methods=['POST'])
def save_progress_session():
    """Save one game session result."""
    data = request.get_json(silent=True) or {}

    user_id = (data.get('user_id') or 'demo-user').strip()
    patient_name = (data.get('patient_name') or '').strip()
    game_id = (data.get('game_id') or '').strip()

    if not patient_name:
        patient_name = display_name_from_user_id(user_id)

    if not game_id:
        return jsonify({'error': 'game_id is required'}), 400

    try:
        duration_seconds = max(int(data.get('duration_seconds', 0)), 0)
        score = max(int(data.get('score', 0)), 0)
        reps = max(int(data.get('reps', 0)), 0)
        accuracy = float(data.get('accuracy', 0))
        accuracy = min(max(accuracy, 0), 100)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid numeric fields'}), 400

    completed_at = data.get('completed_at') or datetime.utcnow().isoformat() + 'Z'
    created_at = datetime.utcnow().isoformat() + 'Z'

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO sessions (
            user_id, patient_name, game_id, duration_seconds, score, reps, accuracy, completed_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, patient_name, game_id, duration_seconds, score, reps, accuracy, completed_at, created_at)
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()

    return jsonify({'status': 'saved', 'session_id': session_id})


@app.route('/api/progress/summary')
def progress_summary():
    """Get summarized progress for a user."""
    user_id = (request.args.get('user_id') or 'demo-user').strip()

    conn = get_db_connection()

    totals = conn.execute(
        """
        SELECT
            COUNT(*) AS total_sessions,
            COALESCE(SUM(duration_seconds), 0) AS total_duration_seconds,
            COALESCE(MAX(score), 0) AS best_score,
            COALESCE(MAX(completed_at), '') AS last_played
        FROM sessions
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    per_game_rows = conn.execute(
        """
        SELECT
            game_id,
            COUNT(*) AS sessions,
            COALESCE(MAX(score), 0) AS best_score,
            COALESCE(AVG(accuracy), 0) AS avg_accuracy,
            COALESCE(SUM(duration_seconds), 0) AS total_duration_seconds
        FROM sessions
        WHERE user_id = ?
        GROUP BY game_id
        """,
        (user_id,)
    ).fetchall()

    recent_rows = conn.execute(
        """
        SELECT game_id, score, reps, accuracy, duration_seconds, completed_at
        FROM sessions
        WHERE user_id = ?
        ORDER BY completed_at DESC
        LIMIT 10
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    return jsonify({
        'user_id': user_id,
        'total_sessions': int(totals['total_sessions']),
        'total_duration_seconds': int(totals['total_duration_seconds']),
        'best_score': int(totals['best_score']),
        'last_played': totals['last_played'],
        'per_game': [dict(row) for row in per_game_rows],
        'recent_sessions': [dict(row) for row in recent_rows]
    })


@app.route('/api/patients')
def list_patients():
    """Search/list patients with usage metadata for switch/search UI."""
    query = (request.args.get('q') or '').strip()
    normalized_query = query.lower()

    try:
        limit = int(request.args.get('limit', 25))
    except (TypeError, ValueError):
        limit = 25
    limit = max(1, min(limit, 100))

    conn = get_db_connection()
    if normalized_query:
        like = f"%{normalized_query}%"
        rows = conn.execute(
            """
            SELECT
                s.user_id,
                COALESCE(
                    (
                        SELECT s2.patient_name
                        FROM sessions s2
                        WHERE s2.user_id = s.user_id AND s2.patient_name <> ''
                        ORDER BY s2.completed_at DESC
                        LIMIT 1
                    ),
                    ''
                ) AS patient_name,
                COUNT(*) AS sessions,
                COALESCE(MAX(s.completed_at), '') AS last_used,
                (
                    COALESCE(SUM(s.score), 0)
                ) AS total_points
            FROM sessions s
            WHERE LOWER(s.user_id) LIKE ? OR LOWER(s.patient_name) LIKE ?
            GROUP BY s.user_id
            ORDER BY last_used DESC
            LIMIT ?
            """,
            (like, like, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT
                s.user_id,
                COALESCE(
                    (
                        SELECT s2.patient_name
                        FROM sessions s2
                        WHERE s2.user_id = s.user_id AND s2.patient_name <> ''
                        ORDER BY s2.completed_at DESC
                        LIMIT 1
                    ),
                    ''
                ) AS patient_name,
                COUNT(*) AS sessions,
                COALESCE(MAX(s.completed_at), '') AS last_used,
                (
                    COALESCE(SUM(s.score), 0)
                ) AS total_points
            FROM sessions s
            GROUP BY s.user_id
            ORDER BY last_used DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
    conn.close()

    patients = []
    for row in rows:
        entry = dict(row)
        if not entry.get('patient_name'):
            entry['patient_name'] = display_name_from_user_id(entry.get('user_id', ''))
        patients.append(entry)

    return jsonify({'patients': patients})


@app.route('/api/progress/patient_data', methods=['DELETE'])
def delete_patient_data():
    """Delete all sessions for a patient/user profile."""
    user_id = (request.args.get('user_id') or '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    deleted = cursor.rowcount if cursor.rowcount is not None else 0
    conn.close()

    return jsonify({'status': 'deleted', 'user_id': user_id, 'deleted_sessions': int(deleted)})


@app.route('/api/progress/leaderboard')
def progress_leaderboard():
    """Get leaderboard across all patients using a blended points formula."""
    try:
        limit = int(request.args.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, 50))

    game_id = (request.args.get('game_id') or '').strip()
    game_filter_sql = ''
    query_params = []
    if game_id:
        game_filter_sql = 'WHERE s.game_id = ?'
        query_params.append(game_id)

    conn = get_db_connection()
    leaderboard_rows = conn.execute(
        f"""
        SELECT
            s.user_id,
            COALESCE(
                (
                    SELECT s2.patient_name
                    FROM sessions s2
                    WHERE s2.user_id = s.user_id AND s2.patient_name <> ''
                    ORDER BY s2.completed_at DESC
                    LIMIT 1
                ),
                ''
            ) AS patient_name,
            COUNT(*) AS sessions,
            COALESCE(SUM(s.score), 0) AS total_score,
            COALESCE(SUM(s.reps), 0) AS total_reps,
            COALESCE(SUM(s.duration_seconds), 0) AS total_duration_seconds,
            COALESCE(MAX(s.score), 0) AS best_score,
            COALESCE(MAX(s.completed_at), '') AS last_played,
            (
                COALESCE(SUM(s.score), 0)
            ) AS total_points
        FROM sessions s
        {game_filter_sql}
        GROUP BY s.user_id
        ORDER BY total_points DESC, total_score DESC, sessions DESC, last_played DESC
        LIMIT ?
        """,
        tuple(query_params + [limit])
    ).fetchall()
    conn.close()

    leaderboard = []
    for row in leaderboard_rows:
        entry = dict(row)
        if not entry.get('patient_name'):
            entry['patient_name'] = display_name_from_user_id(entry.get('user_id', ''))
        leaderboard.append(entry)

    return jsonify({
        'leaderboard': leaderboard
    })

def generate_frames():
    """Generate video frames from current game"""
    global output_frame, frame_lock
    
    cap = cv2.VideoCapture(0)
    
    while camera_active:
        success, frame = cap.read()
        if not success:
            break
        
        # Process frame with current game logic here
        # (This is a simplified version - you'd integrate your game logic)
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    cap.release()

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    init_progress_db()
    print("="*60)
    print("🏥 Rehab Games Platform Server")
    print("="*60)
    print("Starting Flask server...")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("="*60)
    app.run(debug=True, threaded=True, port=5000)
