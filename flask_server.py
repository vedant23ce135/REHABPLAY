"""
Flask Backend for Rehab Games Platform
======================================
This allows streaming Python games to web browser
Run: python flask_server.py
"""

from flask import Flask, render_template, Response, jsonify, request, session, redirect, url_for
from flask_cors import CORS
import cv2
import threading
import base64
import importlib.util
import sqlite3
import hashlib
import os
import re
from pathlib import Path
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, 
           static_folder='web_platform',
           template_folder='web_platform')
CORS(app)
app.config['SECRET_KEY'] = os.environ.get('REHABPLAY_SECRET_KEY', 'rehabplay-dev-secret-change-me')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def get_auth_context():
    """Return authenticated user and organization context from session."""
    user_id = session.get('user_id')
    org_id = session.get('organization_id')
    if not user_id or not org_id:
        return None
    return {
        'user_id': int(user_id),
        'organization_id': int(org_id),
        'email': session.get('email', ''),
        'full_name': session.get('full_name', ''),
        'organization_name': session.get('organization_name', '')
    }


def login_required(view):
    """Protect routes that require an authenticated session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not get_auth_context():
            return redirect(url_for('login_page'))
        return view(*args, **kwargs)
    return wrapped


def api_login_required(view):
    """Protect API routes that require an authenticated session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not get_auth_context():
            return jsonify({'error': 'Authentication required'}), 401
        return view(*args, **kwargs)
    return wrapped


def normalize_org_name(value):
    """Normalize organization name for safe storage/display."""
    text = (value or '').strip()
    if not text:
        return ''
    return ' '.join(text.split())[:80]


def safe_display_name(value):
    """Normalize person display names."""
    text = (value or '').strip()
    if not text:
        return 'Player'
    return ' '.join(text.split())[:80]


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

GAME_CATALOG = {
    'shoulder-rehab': 'Shoulder Rehab',
    'object-catch': 'Pinch and Catch',
    'finger-trainer': 'Finger Trainer',
    'mirror-moves': 'Mirror Moves',
    'shape-tracing': 'Shape Tracing'
}

DAILY_GAME_IDS = list(GAME_CATALOG.keys())


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


def stable_int(seed_text):
    """Generate stable positive integer from a seed string."""
    digest = hashlib.sha256(seed_text.encode('utf-8')).hexdigest()
    return int(digest[:12], 16)


def game_title_from_id(game_id):
    """Return friendly game title for known game ids."""
    return GAME_CATALOG.get(game_id, game_id)


def build_daily_task_plan(user_id, date_key):
    """Create deterministic daily tasks for a user and date."""
    seed_base = f'{user_id}:{date_key}'

    game_one = DAILY_GAME_IDS[stable_int(seed_base + ':game1') % len(DAILY_GAME_IDS)]
    game_two = DAILY_GAME_IDS[stable_int(seed_base + ':game2') % len(DAILY_GAME_IDS)]
    if game_two == game_one:
        game_two = DAILY_GAME_IDS[(DAILY_GAME_IDS.index(game_one) + 1) % len(DAILY_GAME_IDS)]

    min_sessions = 2 + (stable_int(seed_base + ':sessions') % 2)
    score_goal = 90 + (stable_int(seed_base + ':score') % 4) * 30

    return {
        'date_key': date_key,
        'tasks': [
            {
                'id': 'session-count',
                'label': f'Complete {min_sessions} sessions today',
                'type': 'session-count',
                'target': min_sessions
            },
            {
                'id': 'play-specific',
                'label': f'Play {game_title_from_id(game_one)} once',
                'type': 'play-game',
                'target': 1,
                'game_id': game_one
            },
            {
                'id': 'score-goal',
                'label': f'Score {score_goal}+ in {game_title_from_id(game_two)}',
                'type': 'score-game',
                'target': score_goal,
                'game_id': game_two
            }
        ]
    }


def fetch_user_day_sessions(conn, organization_id, user_id, date_key):
    """Fetch one user's sessions for an org/date key (YYYY-MM-DD)."""
    return conn.execute(
        """
        SELECT game_id, score, duration_seconds, completed_at
        FROM sessions
        WHERE organization_id = ? AND user_id = ? AND completed_at LIKE ?
        ORDER BY completed_at DESC
        """,
        (organization_id, user_id, f'{date_key}%')
    ).fetchall()


def evaluate_daily_tasks(plan, day_sessions):
    """Evaluate daily task progress from a task plan and day sessions."""
    evaluated = []
    for task in plan['tasks']:
        progress = 0
        if task['type'] == 'session-count':
            progress = len(day_sessions)
        elif task['type'] == 'play-game':
            progress = sum(1 for session in day_sessions if session['game_id'] == task.get('game_id'))
        elif task['type'] == 'score-game':
            score_values = [int(session['score'] or 0) for session in day_sessions if session['game_id'] == task.get('game_id')]
            progress = max(score_values) if score_values else 0

        target = int(task.get('target', 0))
        done = progress >= target
        evaluated.append({
            **task,
            'progress': int(progress),
            'done': bool(done),
            'display_progress': f"{min(int(progress), target)}/{target}"
        })

    completed = sum(1 for task in evaluated if task['done'])
    return {
        'date_key': plan['date_key'],
        'tasks': evaluated,
        'completed': completed,
        'total': len(evaluated)
    }


def crown_for_completed_tasks(completed):
    """Get crown tier metadata from completed task count."""
    if completed >= 3:
        return {'tier': 'gold', 'label': 'Gold crown'}
    if completed == 2:
        return {'tier': 'silver', 'label': 'Silver crown'}
    if completed == 1:
        return {'tier': 'bronze', 'label': 'Bronze crown'}
    return {'tier': 'none', 'label': 'No crown'}


def init_progress_db():
    """Initialize local progress database."""
    conn = get_db_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            organization_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'owner',
            created_at TEXT NOT NULL,
            last_login_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        )
        """
    )



    row = conn.execute("SELECT id FROM organizations ORDER BY id ASC LIMIT 1").fetchone()
    default_org_id = int(row['id']) if row else None
    if default_org_id is None:
        cursor = conn.execute(
            """
            INSERT INTO organizations (name, account_type, created_at)
            VALUES (?, ?, ?)
            """,
            ('Legacy Workspace', 'organization', datetime.utcnow().isoformat() + 'Z')
        )
        default_org_id = int(cursor.lastrowid)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL DEFAULT 1,
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

    cols = [row['name'] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    if 'patient_name' not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN patient_name TEXT NOT NULL DEFAULT ''")
    if 'organization_id' not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN organization_id INTEGER NOT NULL DEFAULT 1")

    conn.execute(
        """
        UPDATE sessions
        SET organization_id = ?
        WHERE organization_id IS NULL OR organization_id <= 0
        """,
        (default_org_id,)
    )

    conn.commit()
    conn.close()




@app.route('/login')
def login_page():
    """Serve login page."""
    if get_auth_context():
        return redirect(url_for('index'))
    return render_template('auth.html', auth_mode='login')


@app.route('/signup')
def signup_page():
    """Serve signup page."""
    if get_auth_context():
        return redirect(url_for('index'))
    return render_template('auth.html', auth_mode='signup')


@app.route('/logout')
def logout_page():
    """Clear session and return to login page."""
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/api/auth/me')
def auth_me():
    """Get current authenticated user context."""
    auth = get_auth_context()
    if not auth:
        return jsonify({'authenticated': False}), 401
    return jsonify({'authenticated': True, **auth})


@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    """Create a new account and organization, then sign in."""
    data = request.get_json(silent=True) or {}

    full_name = safe_display_name(data.get('full_name') or '')
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    account_type = (data.get('account_type') or 'individual').strip().lower()
    org_name_raw = data.get('organization_name') or ''

    if account_type not in {'individual', 'organization'}:
        return jsonify({'error': 'account_type must be individual or organization'}), 400
    if not EMAIL_RE.match(email):
        return jsonify({'error': 'A valid email is required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    if account_type == 'organization':
        organization_name = normalize_org_name(org_name_raw)
        if not organization_name:
            return jsonify({'error': 'Organization name is required'}), 400
    else:
        organization_name = normalize_org_name(org_name_raw) or f"{full_name}'s Space"

    password_hash = generate_password_hash(password)
    now = datetime.utcnow().isoformat() + 'Z'

    conn = get_db_connection()
    try:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            return jsonify({'error': 'Email already registered'}), 409

        org_cursor = conn.execute(
            """
            INSERT INTO organizations (name, account_type, created_at)
            VALUES (?, ?, ?)
            """,
            (organization_name, account_type, now)
        )
        organization_id = int(org_cursor.lastrowid)

        user_cursor = conn.execute(
            """
            INSERT INTO users (email, password_hash, full_name, organization_id, role, created_at, last_login_at)
            VALUES (?, ?, ?, ?, 'owner', ?, ?)
            """,
            (email, password_hash, full_name, organization_id, now, now)
        )
        user_id = int(user_cursor.lastrowid)
        conn.commit()
    finally:
        conn.close()

    session['user_id'] = user_id
    session['organization_id'] = organization_id
    session['email'] = email
    session['full_name'] = full_name
    session['organization_name'] = organization_name

    return jsonify({
        'status': 'ok',
        'user': {
            'user_id': user_id,
            'organization_id': organization_id,
            'email': email,
            'full_name': full_name,
            'organization_name': organization_name
        }
    })


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Authenticate an existing user."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not EMAIL_RE.match(email):
        return jsonify({'error': 'A valid email is required'}), 400
    if not password:
        return jsonify({'error': 'Password is required'}), 400

    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT
                u.id AS user_id,
                u.email,
                u.password_hash,
                u.full_name,
                u.organization_id,
                o.name AS organization_name
            FROM users u
            JOIN organizations o ON o.id = u.organization_id
            WHERE u.email = ?
            LIMIT 1
            """,
            (email,)
        ).fetchone()

        if not row or not check_password_hash(row['password_hash'], password):
            return jsonify({'error': 'Invalid email or password'}), 401

        now = datetime.utcnow().isoformat() + 'Z'
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, row['user_id']))
        conn.commit()
    finally:
        conn.close()

    session['user_id'] = int(row['user_id'])
    session['organization_id'] = int(row['organization_id'])
    session['email'] = row['email']
    session['full_name'] = row['full_name']
    session['organization_name'] = row['organization_name']

    return jsonify({'status': 'ok'})



@app.route('/')
@login_required
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
@api_login_required
def save_progress_session():
    """Save one game session result."""
    auth = get_auth_context()
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
            organization_id, user_id, patient_name, game_id, duration_seconds, score, reps, accuracy, completed_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (auth['organization_id'], user_id, patient_name, game_id, duration_seconds, score, reps, accuracy, completed_at, created_at)
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()

    return jsonify({'status': 'saved', 'session_id': session_id})


@app.route('/api/progress/summary')
@api_login_required
def progress_summary():
    """Get summarized progress for a user."""
    auth = get_auth_context()
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
        WHERE organization_id = ? AND user_id = ?
        """,
        (auth['organization_id'], user_id)
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
        WHERE organization_id = ? AND user_id = ?
        GROUP BY game_id
        """,
        (auth['organization_id'], user_id)
    ).fetchall()

    recent_rows = conn.execute(
        """
        SELECT game_id, score, reps, accuracy, duration_seconds, completed_at
        FROM sessions
        WHERE organization_id = ? AND user_id = ?
        ORDER BY completed_at DESC
        LIMIT 10
        """,
        (auth['organization_id'], user_id)
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
@api_login_required
def list_patients():
    """Search/list patients with usage metadata for switch/search UI."""
    auth = get_auth_context()
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
            WHERE s.organization_id = ? AND (LOWER(s.user_id) LIKE ? OR LOWER(s.patient_name) LIKE ?)
            GROUP BY s.user_id
            ORDER BY last_used DESC
            LIMIT ?
            """,
            (auth['organization_id'], like, like, limit)
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
            WHERE s.organization_id = ?
            GROUP BY s.user_id
            ORDER BY last_used DESC
            LIMIT ?
            """,
            (auth['organization_id'], limit)
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
@api_login_required
def delete_patient_data():
    """Delete all sessions for a patient/user profile."""
    auth = get_auth_context()
    user_id = (request.args.get('user_id') or '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        "DELETE FROM sessions WHERE organization_id = ? AND user_id = ?",
        (auth['organization_id'], user_id)
    )
    conn.commit()
    deleted = cursor.rowcount if cursor.rowcount is not None else 0
    conn.close()

    return jsonify({'status': 'deleted', 'user_id': user_id, 'deleted_sessions': int(deleted)})


@app.route('/api/progress/leaderboard')
@api_login_required
def progress_leaderboard():
    """Get leaderboard across all patients using a blended points formula."""
    auth = get_auth_context()
    try:
        limit = int(request.args.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, 50))

    game_id = (request.args.get('game_id') or '').strip()
    where_parts = ['s.organization_id = ?']
    query_params = [auth['organization_id']]
    if game_id:
        where_parts.append('s.game_id = ?')
        query_params.append(game_id)

    where_sql = 'WHERE ' + ' AND '.join(where_parts)

    conn = get_db_connection()
    date_key = datetime.utcnow().strftime('%Y-%m-%d')
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
        {where_sql}
        GROUP BY s.user_id
        ORDER BY total_points DESC, total_score DESC, sessions DESC, last_played DESC
        LIMIT ?
        """,
        tuple(query_params + [limit])
    ).fetchall()

    leaderboard = []
    for row in leaderboard_rows:
        entry = dict(row)
        if not entry.get('patient_name'):
            entry['patient_name'] = display_name_from_user_id(entry.get('user_id', ''))

        plan = build_daily_task_plan(entry.get('user_id', ''), date_key)
        day_sessions = fetch_user_day_sessions(conn, auth['organization_id'], entry.get('user_id', ''), date_key)
        evaluation = evaluate_daily_tasks(plan, day_sessions)
        crown = crown_for_completed_tasks(evaluation['completed'])
        entry['crown_tier'] = crown['tier']
        entry['crown_label'] = crown['label']
        entry['daily_tasks_completed'] = int(evaluation['completed'])
        entry['daily_tasks_total'] = int(evaluation['total'])

        leaderboard.append(entry)

    conn.close()

    return jsonify({
        'leaderboard': leaderboard
    })


@app.route('/api/progress/daily_tasks')
@api_login_required
def progress_daily_tasks():
    """Get deterministic daily tasks, progress, and crown tier for one user."""
    auth = get_auth_context()
    user_id = (request.args.get('user_id') or 'demo-user').strip()
    date_key = datetime.utcnow().strftime('%Y-%m-%d')

    plan = build_daily_task_plan(user_id, date_key)

    conn = get_db_connection()
    day_sessions = fetch_user_day_sessions(conn, auth['organization_id'], user_id, date_key)
    conn.close()

    evaluation = evaluate_daily_tasks(plan, day_sessions)
    crown = crown_for_completed_tasks(evaluation['completed'])

    return jsonify({
        'user_id': user_id,
        'date_key': date_key,
        'tasks': evaluation['tasks'],
        'completed': int(evaluation['completed']),
        'total': int(evaluation['total']),
        'crown_tier': crown['tier'],
        'crown_label': crown['label']
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
    server_host = os.environ.get('REHABPLAY_HOST', '0.0.0.0')
    server_port = int(os.environ.get('REHABPLAY_PORT', '5000'))
    server_debug = os.environ.get('REHABPLAY_DEBUG', '1') == '1'

    print("="*60)
    print("🏥 Rehab Games Platform Server")
    print("="*60)
    print("Starting Flask server...")
    print(f"Host: {server_host}  Port: {server_port}  Debug: {server_debug}")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("="*60)
    app.run(host=server_host, debug=server_debug, threaded=True, port=server_port)
