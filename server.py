import json
import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request, session, redirect

BASE_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = BASE_DIR / 'config.json'

DEFAULT_CONFIG = {
    "target_url": "https://fb.qdd.ink",
    "copyright": "© 2025 qdd.ink · 保留所有权利",
    "contact": "https://t.me/epay413"
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(data):
    # 从现有配置开始，保留未知字段（例如 admin_password）
    cfg = load_config()
    for key in ("target_url", "copyright", "contact"):
        if key in data and isinstance(data[key], str):
            cfg[key] = data[key]
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg

def save_admin_password(new_password: str):
    cfg = load_config()
    cfg["admin_password"] = new_password
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return True

app = Flask(__name__, static_folder=str(BASE_DIR))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

def is_authed():
    return bool(session.get('authed'))

@app.get('/')
def index():
    return send_from_directory(str(BASE_DIR), 'index.html')

@app.get('/admin')
def admin():
    if not is_authed():
        return redirect('/login')
    return send_from_directory(str(BASE_DIR), 'admin.html')

@app.get('/login')
def login_page():
    return send_from_directory(str(BASE_DIR), 'login.html')

@app.post('/login')
def login_action():
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        data = {}
    password = (data.get('password') or '').strip()
    # 优先使用存储在配置中的管理员密码，其次使用环境变量，最后使用默认值
    cfg = load_config()
    expected = (cfg.get('admin_password') or os.environ.get('ADMIN_PASSWORD') or 'admin123')
    if password and password == expected:
        session['authed'] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "invalid_password"}), 401

@app.post('/logout')
def logout_action():
    session.clear()
    return jsonify({"ok": True})

@app.get('/api/config')
def api_get_config():
    # 对外隐藏敏感字段（如 admin_password）
    cfg = load_config()
    safe = {k: v for k, v in cfg.items() if k != 'admin_password'}
    return jsonify(safe)

@app.post('/api/config')
def api_set_config():
    if not is_authed():
        return jsonify({"error": "unauthorized"}), 401
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        data = {}
    cfg = save_config(data)
    safe = {k: v for k, v in cfg.items() if k != 'admin_password'}
    return jsonify(safe)

@app.post('/api/admin/password')
def api_change_password():
    if not is_authed():
        return jsonify({"error": "unauthorized"}), 401
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        data = {}
    current = (data.get('current_password') or '').strip()
    new = (data.get('new_password') or '').strip()
    confirm = (data.get('confirm_password') or '').strip()
    cfg = load_config()
    expected = (cfg.get('admin_password') or os.environ.get('ADMIN_PASSWORD') or 'admin123')
    if not current or not new:
        return jsonify({"ok": False, "error": "missing_fields"}), 400
    if current != expected:
        return jsonify({"ok": False, "error": "wrong_current"}), 403
    if len(new) < 6:
        return jsonify({"ok": False, "error": "too_short"}), 400
    if confirm and confirm != new:
        return jsonify({"ok": False, "error": "mismatch"}), 400
    save_admin_password(new)
    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8100'))
    app.run(host='0.0.0.0', port=port)