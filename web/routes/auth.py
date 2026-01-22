# routes/auth.py
# Epic and Amazon authentication routes

import subprocess
from flask import Blueprint, request, jsonify

auth_bp = Blueprint('auth', __name__)

# Session storage for Amazon auth flow
_amazon_auth_sessions = {}


@auth_bp.route("/api/epic/status", methods=["GET"])
def epic_auth_status():
    """Check Epic Games authentication status via Legendary."""
    # Import here to avoid circular imports
    from ..sources.epic import is_legendary_installed, check_authentication

    try:
        if not is_legendary_installed():
            return jsonify({
                "success": True,
                "installed": False,
                "authenticated": False,
                "message": "Legendary CLI is not installed"
            })

        is_auth, username, error = check_authentication()

        if error == "corrective_action":
            return jsonify({
                "success": True,
                "installed": True,
                "authenticated": False,
                "needs_reauth": True,
                "message": "Epic requires you to accept updated terms. Please re-authenticate."
            })

        return jsonify({
            "success": True,
            "installed": True,
            "authenticated": is_auth,
            "username": username,
            "message": f"Logged in as {username}" if is_auth else "Not authenticated"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/epic/auth", methods=["POST"])
def epic_authenticate():
    """Authenticate with Epic Games using an authorization code."""
    # Import here to avoid circular imports
    from ..sources.epic import is_legendary_installed, check_authentication

    try:
        if not is_legendary_installed():
            return jsonify({
                "success": False,
                "error": "Legendary CLI is not installed. Please install it first."
            }), 400

        data = request.get_json() or {}
        auth_code = data.get("code", "").strip()

        if not auth_code:
            return jsonify({
                "success": False,
                "error": "Authorization code is required"
            }), 400

        # Run legendary auth with the provided code
        result = subprocess.run(
            ["legendary", "auth", "--code", auth_code],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Verify authentication succeeded
            is_auth, username, _ = check_authentication()
            if is_auth:
                return jsonify({
                    "success": True,
                    "message": f"Successfully authenticated as {username}",
                    "username": username
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Authentication appeared to succeed but verification failed"
                }), 500
        else:
            error_msg = result.stderr.strip() if result.stderr else "Authentication failed"
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400

    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Authentication timed out"
        }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/amazon/auth/start", methods=["POST"])
def amazon_auth_start():
    """Start Amazon OAuth flow via Nile - returns login URL."""
    try:
        from ..sources.amazon import is_nile_installed, start_auth, logout, check_auth_status
        import uuid

        if not is_nile_installed():
            return jsonify({"success": False, "error": "Nile is not installed"}), 500

        # Log out first if already authenticated (for re-authentication)
        status = check_auth_status()
        if status.get("authenticated"):
            logout()

        auth_data, error = start_auth()
        if error:
            return jsonify({"success": False, "error": error}), 500

        # Store auth credentials with a session ID
        session_id = str(uuid.uuid4())
        _amazon_auth_sessions[session_id] = auth_data

        # Clean up old sessions (keep only last 10)
        if len(_amazon_auth_sessions) > 10:
            oldest = list(_amazon_auth_sessions.keys())[:-10]
            for key in oldest:
                del _amazon_auth_sessions[key]

        return jsonify({
            "success": True,
            "login_url": auth_data.get("login_url"),
            "session_id": session_id,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/amazon/auth/complete", methods=["POST"])
def amazon_auth_complete():
    """Complete Amazon OAuth flow - register with auth code."""
    try:
        from ..sources.amazon import complete_auth
        from urllib.parse import urlparse, parse_qs

        data = request.get_json() or {}
        code = data.get("code", "").strip()
        session_id = data.get("session_id", "").strip()

        if not code:
            return jsonify({"success": False, "error": "Authorization code is required"}), 400

        # Extract code from URL if full URL was pasted
        if "openid.oa2.authorization_code=" in code:
            parsed = urlparse(code)
            params = parse_qs(parsed.query)
            code = params.get("openid.oa2.authorization_code", [code])[0]

        # Get stored auth credentials
        auth_data = _amazon_auth_sessions.pop(session_id, {}) if session_id else {}

        success, message = complete_auth(
            code,
            client_id=auth_data.get("client_id"),
            code_verifier=auth_data.get("code_verifier"),
            serial=auth_data.get("serial"),
        )

        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "error": message}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/amazon/auth/status", methods=["GET"])
def amazon_auth_status():
    """Check Amazon authentication status via Nile."""
    try:
        from ..sources.amazon import is_nile_installed, check_auth_status

        if not is_nile_installed():
            return jsonify({
                "authenticated": False,
                "nile_installed": False,
                "error": "Nile is not installed"
            })

        status = check_auth_status()
        return jsonify({
            "authenticated": status.get("authenticated", False),
            "nile_installed": True,
            "username": status.get("username"),
            "error": status.get("error"),
        })

    except Exception as e:
        return jsonify({"authenticated": False, "error": str(e)})
