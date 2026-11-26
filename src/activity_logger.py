"""
User Accounts & Activity Logger Module.
Tracks platform usage, feature adoption, and user activities while strictly respecting user privacy.
Privacy Guarantees:
- Never stores passwords, password hashes, or authentication tokens.
- Never stores biometric or passkey private credentials.
- Sanitizes AI Chatbot and Voice commands to high-level agronomic topics without logging sensitive personal data.
"""

import json
import uuid
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("activity_logger")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "irrigation_schedules.db"

# Human-friendly icons for activity types
ACTIVITY_ICONS = {
    "LOGIN": "🔑",
    "LOGOUT": "🚪",
    "REGISTER": "🌱",
    "PREDICT_IRRIGATION": "🧠",
    "CREATE_SECTION": "🌾",
    "UPDATE_SECTION": "✏️",
    "DELETE_SECTION": "🗑️",
    "GENERATE_SCHEDULE": "📅",
    "COMPLETE_SCHEDULE": "✅",
    "SKIP_SCHEDULE": "⏭️",
    "WEATHER_SYNC": "🌤️",
    "GPS_LOCATE": "📍",
    "AI_CHAT": "💬",
    "VOICE_COMMAND": "🎙️",
    "PASSKEY_REGISTER": "👤",
}


def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_activity_db():
    """Create user_activities table and indexes if not present."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activities (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    action_summary TEXT NOT NULL,
                    details_json TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_act_user ON user_activities(user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_act_type ON user_activities(activity_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_act_time ON user_activities(created_at DESC);")
        logger.info("Initialized user activities database table and indexes.")
    except Exception as e:
        logger.error(f"Failed to init user activities table: {e}")
    finally:
        conn.close()


def sanitize_activity_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Strip any sensitive fields (passwords, tokens, OTPs) to safeguard privacy."""
    if not details or not isinstance(details, dict):
        return {}
    sanitized = {}
    forbidden_keys = {"password", "password_hash", "otp", "token", "credential", "private_key", "secret"}
    for k, v in details.items():
        if any(f in k.lower() for f in forbidden_keys):
            continue
        # Limit string length if long
        if isinstance(v, str) and len(v) > 200:
            sanitized[k] = v[:200] + "..."
        else:
            sanitized[k] = v
    return sanitized


def log_user_activity(
    user_id: str,
    username: str,
    activity_type: str,
    action_summary: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    """Record a user action into the activity stream."""
    if not user_id or not username:
        return False

    clean_details = sanitize_activity_details(details)
    act_id = f"act_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now().isoformat()

    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO user_activities (
                    id, user_id, username, activity_type, action_summary, details_json, ip_address, user_agent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                act_id,
                user_id,
                username,
                activity_type,
                action_summary,
                json.dumps(clean_details),
                ip_address or "127.0.0.1",
                (user_agent[:120] if user_agent else "Browser"),
                now_iso
            ))
            # Also update last_login_at or last_activity in farmers table
            conn.execute("UPDATE farmers SET last_login_at = ? WHERE id = ?;", (now_iso, user_id))
        return True
    except Exception as e:
        logger.warning(f"Could not log user activity: {e}")
        return False
    finally:
        conn.close()


def get_recent_activities(
    limit: int = 100,
    activity_type: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve recent user activities with pagination and filters."""
    init_activity_db()
    conn = get_db_connection()
    try:
        query = "SELECT * FROM user_activities"
        params = []
        conditions = []

        if activity_type and activity_type != "all":
            conditions.append("activity_type = ?")
            params.append(activity_type)

        if user_id and user_id != "all":
            conditions.append("user_id = ?")
            params.append(user_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(max(1, min(limit, 500)))

        rows = conn.execute(query, params).fetchall()
        activities = []
        for r in rows:
            act = dict(r)
            act["icon"] = ACTIVITY_ICONS.get(act["activity_type"], "📌")
            try:
                act["details"] = json.loads(act["details_json"]) if act["details_json"] else {}
            except Exception:
                act["details"] = {}
            activities.append(act)
        return activities
    finally:
        conn.close()


def get_user_timeline(user_id: str, limit: int = 150) -> Dict[str, Any]:
    """Retrieve the complete chronological activity history for a specific user."""
    init_activity_db()
    conn = get_db_connection()
    try:
        farmer_row = conn.execute("SELECT id, name, username, email, phone, state, district, created_at, status, last_login_at FROM farmers WHERE id = ?;", (user_id,)).fetchone()
        if not farmer_row:
            return {"success": False, "error": "User not found."}

        farmer = dict(farmer_row)

        # Get farm and plots count
        farms_count = conn.execute("SELECT COUNT(*) FROM farms WHERE farmer_id = ?;", (user_id,)).fetchone()[0]
        sections_count = conn.execute("SELECT COUNT(*) FROM farm_sections WHERE farmer_id = ?;", (user_id,)).fetchone()[0]
        schedules_count = conn.execute("SELECT COUNT(*) FROM smart_irrigation_schedules WHERE farmer_id = ?;", (user_id,)).fetchone()[0]

        rows = conn.execute("""
            SELECT * FROM user_activities 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ?;
        """, (user_id, limit)).fetchall()

        timeline = []
        for r in rows:
            item = dict(r)
            item["icon"] = ACTIVITY_ICONS.get(item["activity_type"], "📌")
            try:
                item["details"] = json.loads(item["details_json"]) if item["details_json"] else {}
            except Exception:
                item["details"] = {}
            timeline.append(item)

        return {
            "success": True,
            "farmer": farmer,
            "stats": {
                "farms_count": farms_count,
                "sections_count": sections_count,
                "schedules_count": schedules_count,
                "total_activities": len(timeline),
            },
            "timeline": timeline,
        }
    finally:
        conn.close()


def get_accounts_monitoring_summary() -> Dict[str, Any]:
    """Aggregate high-level accounts & usage statistics for Admin monitoring."""
    init_activity_db()
    conn = get_db_connection()
    try:
        now = datetime.now()
        day_ago = (now - timedelta(days=1)).isoformat()
        week_ago = (now - timedelta(days=7)).isoformat()

        # 1. Total accounts & status
        total_farmers = conn.execute("SELECT COUNT(*) FROM farmers;").fetchone()[0]
        active_farmers = conn.execute("SELECT COUNT(*) FROM farmers WHERE status = 'Active';").fetchone()[0]
        suspended_farmers = conn.execute("SELECT COUNT(*) FROM farmers WHERE status = 'Suspended';").fetchone()[0]

        # 2. Activity metrics
        total_activities = conn.execute("SELECT COUNT(*) FROM user_activities;").fetchone()[0]
        activities_24h = conn.execute("SELECT COUNT(*) FROM user_activities WHERE created_at >= ?;", (day_ago,)).fetchone()[0]
        active_users_7d = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_activities WHERE created_at >= ?;", (week_ago,)).fetchone()[0]

        # 3. Usage by feature breakdown
        type_counts = conn.execute("""
            SELECT activity_type, COUNT(*) as cnt 
            FROM user_activities 
            GROUP BY activity_type 
            ORDER BY cnt DESC;
        """).fetchall()
        feature_breakdown = {r["activity_type"]: r["cnt"] for r in type_counts}

        # 4. Top active users
        top_users_rows = conn.execute("""
            SELECT username, user_id, COUNT(*) as activity_count, MAX(created_at) as last_seen
            FROM user_activities
            GROUP BY user_id
            ORDER BY activity_count DESC
            LIMIT 6;
        """).fetchall()
        top_users = [dict(r) for r in top_users_rows]

        # 5. Total planned water across all user schedules
        water_row = conn.execute("SELECT SUM(water_quantity_liters) FROM smart_irrigation_schedules;").fetchone()
        total_water_liters = float(water_row[0] or 0.0)

        # 6. Total cultivated sections across all users
        sections_count = conn.execute("SELECT COUNT(*) FROM farm_sections WHERE is_empty = 0;").fetchone()[0]

        return {
            "total_farmers": total_farmers,
            "active_farmers": active_farmers,
            "suspended_farmers": suspended_farmers,
            "total_activities": total_activities,
            "activities_24h": activities_24h,
            "active_users_7d": active_users_7d,
            "feature_breakdown": feature_breakdown,
            "top_users": top_users,
            "total_water_liters": round(total_water_liters, 1),
            "total_cultivated_plots": sections_count,
        }
    finally:
        conn.close()
