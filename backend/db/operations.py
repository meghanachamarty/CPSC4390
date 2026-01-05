"""minimized crud operations (no content extraction, simpler).
"""
from typing import List, Optional, Dict, Any
from .client import get_db, get_storage

# ============================================
# user operations
# ============================================

def create_user(
    auth_user_id: str,
    email: str,
    full_name: Optional[str] = None,
    canvas_api_token: Optional[str] = None
) -> Dict[str, Any]:
    """create new user"""
    db = get_db()
    data = {
        'auth_user_id': auth_user_id,
        'email': email,
        'full_name': full_name,
        'canvas_api_token': canvas_api_token
    }
    response = db.table('users').insert(data).execute()
    return response.data[0]

def get_user_by_auth_id(auth_user_id: str) -> Optional[Dict[str, Any]]:
    """get user by auth id"""
    db = get_db()
    response = db.table('users').select('*').eq('auth_user_id', auth_user_id).single().execute()
    return response.data

def update_user_canvas_token(user_id: str, canvas_api_token: str) -> Dict[str, Any]:
    """update canvas api token"""
    db = get_db()
    response = db.table('users').update({'canvas_api_token': canvas_api_token}).eq('id', user_id).execute()
    return response.data[0]

# ============================================
# institution operations
# ============================================

def create_institution(
    name: str,
    canvas_domain: str,
    canvas_base_url: str
) -> Dict[str, Any]:
    """create canvas institution"""
    db = get_db()
    data = {
        'name': name,
        'canvas_domain': canvas_domain,
        'canvas_base_url': canvas_base_url
    }
    response = db.table('canvas_institutions').insert(data).execute()
    return response.data[0]

def get_institution_by_domain(canvas_domain: str) -> Optional[Dict[str, Any]]:
    """get institution by domain"""
    db = get_db()
    response = db.table('canvas_institutions').select('*').eq('canvas_domain', canvas_domain).single().execute()
    return response.data

def get_all_institutions() -> List[Dict[str, Any]]:
    """get all institutions"""
    db = get_db()
    response = db.table('canvas_institutions').select('*').execute()
    return response.data

# ============================================
# course operations
# ============================================

def create_course(
    user_id: str,
    course_code: str,
    course_name: str,
    institution_id: Optional[str] = None,
    canvas_course_id: Optional[str] = None,
    semester: Optional[str] = None
) -> Dict[str, Any]:
    """create new course"""
    db = get_db()
    data = {
        'user_id': user_id,
        'institution_id': institution_id,
        'canvas_course_id': canvas_course_id,
        'course_code': course_code,
        'course_name': course_name,
        'semester': semester
    }
    response = db.table('courses').insert(data).execute()
    return response.data[0]

def get_user_courses(user_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
    """get user's courses"""
    db = get_db()
    query = db.table('courses').select('*, canvas_institutions(*)').eq('user_id', user_id)
    
    if active_only:
        query = query.eq('is_active', True)
    
    response = query.execute()
    return response.data

def get_course_by_id(course_id: str) -> Optional[Dict[str, Any]]:
    """get course by id"""
    db = get_db()
    response = db.table('courses').select('*, canvas_institutions(*)').eq('id', course_id).single().execute()
    return response.data

def update_course_sync_time(course_id: str) -> Dict[str, Any]:
    """update last synced timestamp"""
    from datetime import datetime
    db = get_db()
    response = db.table('courses').update({'last_synced_at': datetime.now().isoformat()}).eq('id', course_id).execute()
    return response.data[0]

def deactivate_course(course_id: str) -> Dict[str, Any]:
    """deactivate course (soft delete)"""
    db = get_db()
    response = db.table('courses').update({'is_active': False}).eq('id', course_id).execute()
    return response.data[0]

# ============================================
# file operations (minimized)
# ============================================

def create_course_file(
    course_id: str,
    filename: str,
    file_url: str,
    storage_path: str,
    file_type: Optional[str] = None,
    file_size: Optional[int] = None,
    mime_type: Optional[str] = None
) -> Dict[str, Any]:
    """create course file record (no content field)"""
    db = get_db()
    data = {
        'course_id': course_id,
        'filename': filename,
        'file_type': file_type,
        'file_url': file_url,
        'storage_path': storage_path,
        'file_size': file_size,
        'mime_type': mime_type
    }
    response = db.table('course_files').insert(data).execute()
    return response.data[0]

def get_course_files(course_id: str) -> List[Dict[str, Any]]:
    """get all files for a course"""
    db = get_db()
    response = db.table('course_files').select('*').eq('course_id', course_id).execute()
    return response.data

def get_all_user_files(user_id: str) -> List[Dict[str, Any]]:
    """get all files across user's courses"""
    db = get_db()
    response = (db.table('course_files')
                .select('*, courses!inner(user_id, course_code, course_name)')
                .eq('courses.user_id', user_id)
                .eq('courses.is_active', True)
                .execute())
    return response.data

def delete_course_file(file_id: str) -> bool:
    """delete file record"""
    db = get_db()
    db.table('course_files').delete().eq('id', file_id).execute()
    return True

# ============================================
# storage operations
# ============================================

def upload_file(
    user_id: str,
    course_id: str,
    filename: str,
    file_data: bytes,
    mime_type: Optional[str] = None
) -> Dict[str, Any]:
    """upload file to storage bucket"""
    storage = get_storage()
    
    storage_path = f"{user_id}/{course_id}/{filename}"
    
    response = storage.storage.from_('course-documents').upload(
        path=storage_path,
        file=file_data,
        file_options={
            'content-type': mime_type or 'application/octet-stream',
            'upsert': 'true'
        }
    )
    
    file_url = storage.storage.from_('course-documents').get_public_url(storage_path)
    
    return {
        'storage_path': storage_path,
        'file_url': file_url,
        'size': len(file_data)
    }

def download_file(storage_path: str) -> bytes:
    """download file from storage"""
    storage = get_storage()
    response = storage.storage.from_('course-documents').download(storage_path)
    return response

def delete_file_from_storage(storage_path: str) -> bool:
    """delete file from storage"""
    storage = get_storage()
    storage.storage.from_('course-documents').remove([storage_path])
    return True

# ============================================
# combined operations
# ============================================

def upload_course_file(
    user_id: str,
    course_id: str,
    filename: str,
    file_data: bytes,
    file_type: Optional[str] = None,
    mime_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    upload file to storage and create database record.
    simplified - no text extraction.
    """
    upload_result = None
    try:
        # upload to storage
        upload_result = upload_file(
            user_id=user_id,
            course_id=course_id,
            filename=filename,
            file_data=file_data,
            mime_type=mime_type
        )
        
        # create database record
        file_record = create_course_file(
            course_id=course_id,
            filename=filename,
            file_url=upload_result['file_url'],
            storage_path=upload_result['storage_path'],
            file_type=file_type,
            file_size=upload_result['size'],
            mime_type=mime_type
        )
        
        return file_record
    
    except Exception as e:
        # rollback
        if upload_result:
            try:
                delete_file_from_storage(upload_result['storage_path'])
            except:
                pass
        raise e

def delete_course_file_complete(file_id: str) -> bool:
    """delete file from database and storage"""
    db = get_db()
    
    # get file record
    file_record = db.table('course_files').select('*').eq('id', file_id).single().execute()
    
    if file_record.data:
        # delete from storage
        try:
            delete_file_from_storage(file_record.data['storage_path'])
        except:
            pass
        
        # delete from database
        delete_course_file(file_id)
        return True
    
    return False

# ============================================
# utilities
# ============================================

def health_check() -> Dict[str, bool]:
    """health check"""
    health = {'database': False, 'storage': False}
    
    try:
        db = get_db()
        db.table('users').select('id').limit(1).execute()
        health['database'] = True
    except:
        pass
    
    try:
        storage = get_storage()
        storage.storage.list_buckets()
        health['storage'] = True
    except:
        pass
    
    return health
