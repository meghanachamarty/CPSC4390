"""
database and storage client singleton.
single connection for database + storage.
"""
import os
from supabase import create_client, Client
from typing import Optional

class DatabaseClient:
    """
    singleton pattern for supabase client.
    provides both database and storage access.
    """
    _instance: Optional[Client] = None
    
    @classmethod
    def get_instance(cls) -> Client:
        """
        get or create supabase client.
        this client provides access to:
        - database (PostgreSQL)
        - storage (S3-compatible buckets)
        - auth (user management)
        """
        if cls._instance is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
            
            if not supabase_url or not supabase_key:
                raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            
            cls._instance = create_client(supabase_url, supabase_key)
        
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """reset instance (for testing)"""
        cls._instance = None

# Convenience functions
def get_db() -> Client:
    """get database client (for table operations)"""
    return DatabaseClient.get_instance()

def get_storage() -> Client:
    """
    get storage client (for file operations).
    same client, just semantic naming for clarity.
    
    usage:
        storage = get_storage()
        storage.storage.from_('course-documents').upload(...)
    """
    return DatabaseClient.get_instance()
