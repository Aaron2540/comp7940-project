import json
import logging
from datetime import datetime

import redis

import config

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


def redis_client() -> redis.Redis:
    """Lazy singleton for the Redis connection."""
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis


# -- chat history --

def save_message(user_id: int, role: str, content: str) -> None:
    try:
        r = redis_client()
        key = f"chat:{user_id}"
        msg = json.dumps({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()})
        r.rpush(key, msg)
        r.ltrim(key, -config.MAX_HISTORY, -1)  # keep only recent messages
    except Exception:
        logger.exception("Failed to save message for user %s", user_id)


def get_history(user_id: int) -> list[dict]:
    try:
        r = redis_client()
        raw = r.lrange(f"chat:{user_id}", 0, -1)
        return [json.loads(m) for m in raw]
    except Exception:
        logger.exception("Failed to get history for user %s", user_id)
        return []


def clear_history(user_id: int) -> None:
    try:
        redis_client().delete(f"chat:{user_id}")
    except Exception:
        logger.exception("Failed to clear history for user %s", user_id)


# -- todo / deadline management --

def add_todo(user_id: int, text: str, deadline: str = "") -> dict:
    try:
        r = redis_client()
        todo_id = r.incr(f"todo_seq:{user_id}")
        todo = {"id": todo_id, "text": text, "deadline": deadline, "done": False,
                "created": datetime.utcnow().isoformat()}
        r.hset(f"todos:{user_id}", str(todo_id), json.dumps(todo))
        return todo
    except Exception:
        logger.exception("Failed to add todo for user %s", user_id)
        return {}


def get_todos(user_id: int) -> list[dict]:
    try:
        raw = redis_client().hgetall(f"todos:{user_id}")
        todos = [json.loads(v) for v in raw.values()]
        todos.sort(key=lambda x: x.get("id", 0))
        return todos
    except Exception:
        logger.exception("Failed to get todos for user %s", user_id)
        return []


def complete_todo(user_id: int, todo_id: int) -> bool:
    try:
        r = redis_client()
        raw = r.hget(f"todos:{user_id}", str(todo_id))
        if not raw:
            return False
        todo = json.loads(raw)
        todo["done"] = True
        r.hset(f"todos:{user_id}", str(todo_id), json.dumps(todo))
        return True
    except Exception:
        logger.exception("Failed to complete todo for user %s", user_id)
        return False


def delete_todo(user_id: int, todo_id: int) -> bool:
    try:
        return redis_client().hdel(f"todos:{user_id}", str(todo_id)) > 0
    except Exception:
        logger.exception("Failed to delete todo for user %s", user_id)
        return False


# -- study buddy matching --

def set_profile(user_id: int, username: str, interests: list[str], courses: list[str]) -> None:
    try:
        profile = {"user_id": user_id, "username": username, "interests": interests,
                   "courses": courses, "updated": datetime.utcnow().isoformat()}
        redis_client().hset("profiles", str(user_id), json.dumps(profile))
    except Exception:
        logger.exception("Failed to set profile for user %s", user_id)


def get_profile(user_id: int) -> dict | None:
    try:
        raw = redis_client().hget("profiles", str(user_id))
        return json.loads(raw) if raw else None
    except Exception:
        logger.exception("Failed to get profile for user %s", user_id)
        return None


def find_matches(user_id: int) -> list[dict]:
    """Find users with overlapping interests or courses. Courses weighted higher."""
    try:
        my_profile = get_profile(user_id)
        if not my_profile:
            return []

        my_interests = set(i.lower() for i in my_profile.get("interests", []))
        my_courses = set(c.lower() for c in my_profile.get("courses", []))

        all_profiles = redis_client().hgetall("profiles")
        matches = []
        for uid, raw in all_profiles.items():
            if str(uid) == str(user_id):
                continue
            profile = json.loads(raw)
            their_interests = set(i.lower() for i in profile.get("interests", []))
            their_courses = set(c.lower() for c in profile.get("courses", []))

            common_interests = my_interests & their_interests
            common_courses = my_courses & their_courses
            score = len(common_interests) * 2 + len(common_courses) * 3

            if score > 0:
                matches.append({
                    "username": profile.get("username", "Unknown"),
                    "common_interests": list(common_interests),
                    "common_courses": list(common_courses),
                    "score": score,
                })

        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:5]
    except Exception:
        logger.exception("Failed to find matches for user %s", user_id)
        return []


# -- campus events (sample data) --

SAMPLE_EVENTS = [
    {"id": 1, "title": "AI & Machine Learning Workshop", "date": "2026-04-20", "category": "tech", "location": "Room A101"},
    {"id": 2, "title": "Basketball Tournament", "date": "2026-04-22", "category": "sports", "location": "Sports Hall"},
    {"id": 3, "title": "Career Fair 2026", "date": "2026-04-25", "category": "career", "location": "Main Hall"},
    {"id": 4, "title": "Photography Exhibition", "date": "2026-04-18", "category": "art", "location": "Gallery B"},
    {"id": 5, "title": "Hackathon: Cloud Computing", "date": "2026-04-28", "category": "tech", "location": "Lab C301"},
    {"id": 6, "title": "Music Night", "date": "2026-04-19", "category": "entertainment", "location": "Auditorium"},
    {"id": 7, "title": "Study Group: Data Science", "date": "2026-04-21", "category": "study", "location": "Library Room 2"},
    {"id": 8, "title": "Volunteer: Beach Cleanup", "date": "2026-04-26", "category": "volunteer", "location": "Clearwater Bay"},
    {"id": 9, "title": "Startup Pitch Competition", "date": "2026-04-30", "category": "career", "location": "Innovation Center"},
    {"id": 10, "title": "Movie Night: Interstellar", "date": "2026-05-02", "category": "entertainment", "location": "Lecture Hall D"},
]


def get_events(category: str = "") -> list[dict]:
    if category:
        return [e for e in SAMPLE_EVENTS if e["category"] == category.lower()]
    return SAMPLE_EVENTS


def get_event_categories() -> list[str]:
    return list(set(e["category"] for e in SAMPLE_EVENTS))


# -- request logging & stats --

def log_request(user_id: int, username: str, message: str, response: str, latency_ms: int) -> None:
    try:
        r = redis_client()
        entry = json.dumps({"user_id": user_id, "username": username, "message": message,
                            "response": response[:500], "latency_ms": latency_ms,
                            "timestamp": datetime.utcnow().isoformat()})
        r.lpush("logs:requests", entry)
        r.ltrim("logs:requests", 0, 999)  # keep last 1000 logs
        r.incr("stats:total_requests")
        r.incr(f"stats:user:{user_id}:requests")
    except Exception:
        logger.exception("Failed to log request")


def get_stats() -> dict:
    try:
        r = redis_client()
        total = r.get("stats:total_requests") or "0"
        profiles_count = r.hlen("profiles")
        return {"total_requests": int(total), "registered_users": profiles_count}
    except Exception:
        logger.exception("Failed to get stats")
        return {"total_requests": 0, "registered_users": 0}


def get_recent_logs(count: int = 10) -> list[dict]:
    try:
        raw = redis_client().lrange("logs:requests", 0, count - 1)
        return [json.loads(entry) for entry in raw]
    except Exception:
        logger.exception("Failed to get recent logs")
        return []


def health_check() -> bool:
    try:
        redis_client().ping()
        return True
    except Exception:
        return False
