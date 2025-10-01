from fastapi import APIRouter, Depends, File, Response, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from models import get_db
from core.file import preview_file_from_minio, upload_file_to_minio, download_file, upload_file, upload_file_to_tmp, compress_image_to_target_size
from core.responses import (
    Created,
    Unauthorized,
    common_response,
    InternalServerError,
    BadRequest,
)
from datetime import datetime
from core.security import get_user_from_jwt_token, oauth2_scheme
from schemas.common import NoContentResponse, InternalServerErrorResponse, UnauthorizedResponse
from settings import MINIO_BUCKET
import os

router = APIRouter(tags=["File"])


def sanitize_path_component(component: str) -> str:
    """
    Sanitize path components to avoid file system issues and security vulnerabilities
    """
    import re
    
    if not component or not isinstance(component, str):
        return "unknown"
    
    # Remove null bytes and control characters
    component = ''.join(char for char in component if ord(char) >= 32)
    
    # Replace dangerous characters
    dangerous_chars = ['/', '\\', ':', '*', '?', '"', "'", '<', '>', '|', '\0']
    for char in dangerous_chars:
        component = component.replace(char, '_')
    
    # Handle path traversal attempts
    component = component.replace('..', '_')
    
    # Replace spaces and normalize
    component = component.replace(' ', '_').strip()
    
    # Remove leading/trailing dots and spaces
    component = component.strip('. ')
    
    # Check for Windows reserved names
    windows_reserved = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
    if component.upper() in windows_reserved:
        component = f"safe_{component}"
    
    # Ensure it's not empty and limit length
    if not component:
        component = "unnamed"
    
    # Limit length to prevent filesystem issues
    if len(component) > 100:
        component = component[:100]
    
    # Ensure it doesn't start with dot (hidden file)
    if component.startswith('.'):
        component = 'file_' + component[1:]
    
    return component


def sanitize_file_extension(extension: str) -> str:
    """
    Sanitize and validate file extensions for security
    """
    if not extension:
        return ""
    
    # Remove leading dot if present
    extension = extension.lstrip('.')
    
    # Dangerous executable extensions that should be blocked
    dangerous_extensions = {
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar', 
        'msi', 'dll', 'scf', 'lnk', 'inf', 'reg', 'ps1', 'psm1'
    }
    
    # Check if extension is dangerous
    if extension.lower() in dangerous_extensions:
        extension = f"{extension}_safe"
    
    # Add back the dot
    return f".{extension}" if extension else ""


@router.post(
    "/upload",
    responses={
        "204": {"model": NoContentResponse},
        "500": {"model": InternalServerErrorResponse},
    },
)
async def upload_file_router(
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    try:
        user = get_user_from_jwt_token(db, token)
        if not user:
            return common_response(Unauthorized(message="Invalid/Expired token"))
        
        file_extension = os.path.splitext(file.filename)[1]
        file_name = os.path.splitext(file.filename)[0]
        now = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        
        # Sanitize components for safe file path
        safe_file_name = sanitize_path_component(file_name)
        safe_user_name = sanitize_path_component(user.name)
        safe_extension = sanitize_file_extension(file_extension)
        safe_now = now.replace(' ', '_')
        
        # Compress image files to 1MB before uploading
        processed_file = await compress_image_to_target_size(file, target_size_mb=1.0)
        
        path = await upload_file(
            upload_file=processed_file, 
            path=f"/tmp/{safe_file_name}-{safe_user_name}{safe_now}{safe_extension}"
        )
        
        return common_response(Created(path))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Error upload: \n", e)
        return common_response(BadRequest(message="Failed Upload", data={"detail":str(e)}))


@router.get(
    "/download",
    response_class=FileResponse or UnauthorizedResponse
)
async def dowload_file(
    minio_path: str,
):
    try:
        file_response = download_file(
            path=minio_path,
        )
        if file_response:
            return file_response
        else:
            return Response(status_code=404)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return common_response(InternalServerError(error=str(e)))


