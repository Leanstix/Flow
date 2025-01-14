import hashlib
import time

def generate_room_name(user_ids):
    """
    Generate a unique room name using participants' user IDs and the current timestamp.
    
    Args:
    - user_ids (list): List of user IDs participating in the call.
    
    Returns:
    - str: A unique room name.
    """
    user_string = "-".join(sorted(map(str, user_ids)))  # Ensure IDs are strings and sorted
    timestamp = str(int(time.time()))
    room_hash = hashlib.sha256(f"{user_string}-{timestamp}".encode()).hexdigest()
    return f"room-{room_hash[:12]}"