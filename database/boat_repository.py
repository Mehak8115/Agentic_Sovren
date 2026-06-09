# database/boat_repository.py

import os
import json
import uuid
from datetime import datetime
from database.mongodb import db
from bson import ObjectId
from copy import deepcopy

boats_collection    = db["boats"]
bookings_collection = db["bookings"]

USER_MEMORY_PATH = "data/user_memory.json"


def get_all_boats():
    return list(boats_collection.find({}))


def get_boat_by_id(boat_id: str):
    return boats_collection.find_one({"_id": ObjectId(boat_id)})


def save_booking(booking: dict) -> str:
    data   = deepcopy(booking)
    result = bookings_collection.insert_one(data)
    return str(result.inserted_id)


def get_booking_by_id(booking_id: str):
    return bookings_collection.find_one({"_id": ObjectId(booking_id)})


# ── User memory functions ────────────────────────────────────────────────────

def load_user_memory() -> dict:
    if not os.path.exists(USER_MEMORY_PATH):
        return {"users": {}}
    with open(USER_MEMORY_PATH, "r") as f:
        return json.load(f)


def save_user_memory(data: dict):
    os.makedirs(os.path.dirname(USER_MEMORY_PATH), exist_ok=True)
    with open(USER_MEMORY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_or_create_user(name: str) -> dict:
    """Get user profile by name, or create new one."""
    memory = load_user_memory()
    users  = memory.get("users", {})
    
    # Search by name (case-insensitive)
    for user_id, profile in users.items():
        if profile.get("name", "").lower() == name.lower():
            return profile
    
    # Create new user
    user_id = str(uuid.uuid4())[:8]
    new_user = {
        "user_id":          user_id,
        "name":             name,
        "preferred_location": None,
        "recent_bookings":  [],
        "past_bookings":    [],
        "created_at":       datetime.utcnow().isoformat(),
    }
    users[user_id] = new_user
    memory["users"]  = users
    save_user_memory(memory)
    return new_user


def update_user_booking(user_id: str, booking_id: str, boat_name: str, travel_date: str):
    """Add booking to user's history."""
    memory = load_user_memory()
    users  = memory.get("users", {})
    
    if user_id not in users:
        return
    
    booking_entry = {
        "booking_id":  booking_id,
        "boat_name":   boat_name,
        "travel_date": travel_date,
        "booked_at":   datetime.utcnow().isoformat(),
    }
    
    users[user_id]["recent_bookings"].insert(0, booking_entry)
    
    # Keep only last 3 recent bookings
    if len(users[user_id]["recent_bookings"]) > 3:
        users[user_id]["past_bookings"].extend(users[user_id]["recent_bookings"][3:])
        users[user_id]["recent_bookings"] = users[user_id]["recent_bookings"][:3]
    
    save_user_memory(memory)


def update_user_preference(user_id: str, location: str):
    """Update user's preferred location."""
    memory = load_user_memory()
    users  = memory.get("users", {})
    
    if user_id in users:
        users[user_id]["preferred_location"] = location
        save_user_memory(memory)
