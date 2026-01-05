"""database module exports (4-table schema).
"""

from .client import get_db, get_storage, DatabaseClient
from .operations import (
    # Users
    create_user,
    get_user_by_auth_id,
    update_user_canvas_token,
    
    # Institutions
    create_institution,
    get_institution_by_domain,
    get_all_institutions,
    
    # Courses
    create_course,
    get_user_courses,
    get_course_by_id,
    update_course_sync_time,
    deactivate_course,
    
    # Files
    create_course_file,
    get_course_files,
    get_all_user_files,
    delete_course_file,
    
    # Storage
    upload_file,
    download_file,
    delete_file_from_storage,
    
    # Combined
    upload_course_file,
    delete_course_file_complete,
    
    # Utilities
    health_check
)

__all__ = [
    'get_db', 'get_storage', 'DatabaseClient',
    
    # users
    'create_user', 'get_user_by_auth_id', 'update_user_canvas_token',
    
    # institutions
    'create_institution', 'get_institution_by_domain', 'get_all_institutions',
    
    # courses
    'create_course', 'get_user_courses', 'get_course_by_id',
    'update_course_sync_time', 'deactivate_course',
    
    # files
    'create_course_file', 'get_course_files', 'get_all_user_files',
    'delete_course_file',
    
    # storage
    'upload_file', 'download_file', 'delete_file_from_storage',
    
    # combined
    'upload_course_file', 'delete_course_file_complete',
    
    # utilities
    'health_check',
]
