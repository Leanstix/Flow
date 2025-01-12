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
    # Combine user IDs into a single string
    user_string = "-".join(sorted(user_ids))  # Sorting ensures consistency
    timestamp = str(int(time.time()))  # Current timestamp as string
    
    # Create a unique hash using user string and timestamp
    room_hash = hashlib.sha256(f"{user_string}-{timestamp}".encode()).hexdigest()
    
    # Truncate the hash for brevity and readability
    room_name = f"room-{room_hash[:12]}"
    
    return room_name
