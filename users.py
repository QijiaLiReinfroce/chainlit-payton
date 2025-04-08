"""
User management module for Chainlit application.
Handles user registration, authentication, and storage.
"""
import os
import json
import hashlib
import secrets
from typing import Dict, Optional, List, Tuple

# Path to the user database file
USER_DB_PATH = os.path.join(os.path.dirname(__file__), "user_db.json")

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash a password with a salt for secure storage.
    
    Args:
        password: The password to hash
        salt: Optional salt, generated if not provided
        
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Create a hash with the password and salt
    password_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000  # Number of iterations
    ).hex()
    
    return password_hash, salt

def load_users() -> Dict:
    """
    Load the user database from disk.
    
    Returns:
        Dictionary of users or empty dict if no database exists
    """
    if not os.path.exists(USER_DB_PATH):
        return {}
    
    try:
        with open(USER_DB_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_users(users: Dict) -> None:
    """
    Save the user database to disk.
    
    Args:
        users: Dictionary of user data to save
    """
    with open(USER_DB_PATH, 'w') as f:
        json.dump(users, f, indent=2)

def add_user(username: str, password: str, role: str = "user") -> bool:
    """
    Add a new user to the database.
    
    Args:
        username: Unique username for the new user
        password: Password for the new user
        role: Role for the user (default: "user")
        
    Returns:
        True if user was added, False if username already exists
    """
    users = load_users()
    
    # Check if user already exists
    if username in users:
        return False
    
    # Hash the password with a new salt
    password_hash, salt = hash_password(password)
    
    # Add the user to the database
    users[username] = {
        "username": username,
        "password_hash": password_hash,
        "salt": salt,
        "role": role,
        "created_at": str(secrets.token_hex(8))  # Simple timestamp
    }
    
    # Save the updated database
    save_users(users)
    return True

def verify_user(username: str, password: str) -> Optional[Dict]:
    """
    Verify a user's credentials.
    
    Args:
        username: Username to verify
        password: Password to verify
        
    Returns:
        User data dict if credentials are valid, None otherwise
    """
    users = load_users()
    
    # Check if user exists
    if username not in users:
        return None
    
    user = users[username]
    
    # Get the stored password hash and salt
    stored_hash = user["password_hash"]
    salt = user["salt"]
    
    # Hash the provided password with the stored salt
    calculated_hash, _ = hash_password(password, salt)
    
    # Compare the hashes
    if calculated_hash == stored_hash:
        # Return a copy of the user data without the password hash
        result = user.copy()
        result.pop("password_hash", None)
        return result
    
    return None

def remove_user(username: str) -> bool:
    """
    Remove a user from the database.
    
    Args:
        username: Username to remove
        
    Returns:
        True if user was removed, False if username doesn't exist
    """
    users = load_users()
    
    # Check if user exists
    if username not in users:
        return False
    
    # Remove the user
    del users[username]
    
    # Save the updated database
    save_users(users)
    return True

def list_users() -> List[Dict]:
    """
    List all users in the database.
    
    Returns:
        List of user data dictionaries
    """
    users = load_users()
    
    # Return a list of user data without password hashes
    result = []
    for username, user_data in users.items():
        user_copy = user_data.copy()
        user_copy.pop("password_hash", None)
        result.append(user_copy)
    
    return result

# Initialize the user database if it doesn't exist
if not os.path.exists(USER_DB_PATH):
    # Create an admin user by default
    add_user("admin", "admin", "admin")
    # Add some example users
    add_user("user1", "password1", "user")