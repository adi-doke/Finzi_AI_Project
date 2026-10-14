from __future__ import annotations

from functools import wraps

from flask import g, jsonify, redirect, request, session

SESSION_USER_KEY = "user_phone"
SESSION_NAME_KEY = "user_name"


def login_user(user) -> None:
    session.clear()
    session[SESSION_USER_KEY] = user.phone
    session[SESSION_NAME_KEY] = user.name
    session.permanent = True


def logout_user() -> None:
    session.clear()


def current_user_phone() -> str | None:
    return session.get(SESSION_USER_KEY)


def current_user_name() -> str | None:
    return session.get(SESSION_NAME_KEY)


def require_user_page(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user_phone():
            return redirect(f"/login?next={request.path}")
        return view(*args, **kwargs)

    return wrapper


def require_api_user(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        phone = current_user_phone()
        if not phone:
            return jsonify({"success": False, "message": "Authentication required"}), 401
        g.current_user_phone = phone
        return view(*args, **kwargs)

    return wrapper
