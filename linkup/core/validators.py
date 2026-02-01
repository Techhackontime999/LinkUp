"""
File upload validation and security utilities for the professional network platform.
Implements comprehensive security measures for file uploads including type validation,
size limits, content scanning, and malware protection.
"""

import os
import mimetypes
import hashlib
import logging
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.deconstruct import deconstructible
from PIL import Image

# Try to import python-magic, fall back to mimetypes if not available
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    magic = None

logger = logging.getLogger(__name__)

# File upload security configuration
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
}

ALLOWED_DOCUMENT_TYPES = {
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'text/plain': ['.txt'],
    'text/csv': ['.csv'],
}

ALLOWED_ARCHIVE_TYPES = {
    'application/zip': ['.zip'],
    'application/x-rar-compressed': ['.rar'],
    'application/x-7z-compressed': ['.7z'],
}

# Maximum file sizes (in bytes)
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ARCHIVE_SIZE = 50 * 1024 * 1024  # 50MB

# Dangerous file extensions that should never be allowed
DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
    '.app', '.deb', '.pkg', '.dmg', '.rpm', '.msi', '.run', '.bin',
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.psm1', '.psd1',
    '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl', '.cgi'
}

# Suspicious file signatures (magic bytes) to detect
MALICIOUS_SIGNATURES = [
    b'MZ',  # PE executable
    b'\x7fELF',  # ELF executable
    b'\xca\xfe\xba\xbe',  # Java class file
    b'PK\x03\x04',  # ZIP file (could contain malicious content)
]


@deconstructible
class FileUploadValidator:
    """
    Comprehensive file upload validator that checks file type, size, content,
    and security characteristics to prevent malicious uploads.
    """
    
    def __init__(self, allowed_types=None, max_size=None, check_content=True):
        self.allowed_types = allowed_types or ALLOWED_IMAGE_TYPES
        self.max_size = max_size or MAX_IMAGE_SIZE
        self.check_content = check_content
    
    def __call__(self, file):
        """
        Validate uploaded file for security and compliance.
        
        Args:
            file: Django UploadedFile instance
            
        Raises:
            ValidationError: If file fails any validation check
        """
        if not isinstance(file, UploadedFile):
            raise ValidationError("Invalid file upload.")
        
        # Check file size
        self._validate_file_size(file)
        
        # Check file extension
        self._validate_file_extension(file)
        
        # Check MIME type
        self._validate_mime_type(file)
        
        # Check file content if enabled
        if self.check_content:
            self._validate_file_content(file)
        
        # Security checks
        self._security_scan(file)
        
        logger.info(f"File upload validated successfully: {file.name}")
    
    def _validate_file_size(self, file):
        """Validate file size against maximum allowed size."""
        if file.size > self.max_size:
            size_mb = self.max_size / (1024 * 1024)
            raise ValidationError(
                f"File size ({file.size / (1024 * 1024):.1f}MB) exceeds maximum allowed size ({size_mb:.1f}MB)."
            )
    
    def _validate_file_extension(self, file):
        """Validate file extension against allowed types."""
        if not file.name:
            raise ValidationError("File must have a name.")
        
        file_ext = os.path.splitext(file.name)[1].lower()
        
        # Check for dangerous extensions
        if file_ext in DANGEROUS_EXTENSIONS:
            raise ValidationError(f"File type '{file_ext}' is not allowed for security reasons.")
        
        # Check if extension is in allowed types
        allowed_extensions = []
        for mime_type, extensions in self.allowed_types.items():
            allowed_extensions.extend(extensions)
        
        if file_ext not in allowed_extensions:
            raise ValidationError(
                f"File extension '{file_ext}' is not allowed. "
                f"Allowed extensions: {', '.join(allowed_extensions)}"
            )
    
    def _validate_mime_type(self, file):
        """Validate MIME type using python-magic for accurate detection."""
        try:
            # Reset file pointer
            file.seek(0)
            
            # Read first chunk for MIME type detection
            chunk = file.read(1024)
            file.seek(0)
            
            # Detect MIME type
            if HAS_MAGIC:
                # Use python-magic for accurate detection
                detected_mime = magic.from_buffer(chunk, mime=True)
            else:
                # Fall back to mimetypes module
                detected_mime, _ = mimetypes.guess_type(file.name)
                if not detected_mime:
                    # Try to detect from file content
                    if chunk.startswith(b'\xff\xd8\xff'):
                        detected_mime = 'image/jpeg'
                    elif chunk.startswith(b'\x89PNG'):
                        detected_mime = 'image/png'
                    elif chunk.startswith(b'GIF8'):
                        detected_mime = 'image/gif'
                    elif chunk.startswith(b'%PDF'):
                        detected_mime = 'application/pdf'
                    else:
                        detected_mime = 'application/octet-stream'
            
            # Also check Django's content_type
            declared_mime = file.content_type
            
            # Validate against allowed types
            if detected_mime not in self.allowed_types:
                raise ValidationError(
                    f"File type '{detected_mime}' is not allowed. "
                    f"Allowed types: {', '.join(self.allowed_types.keys())}"
                )
            
            # Check for MIME type spoofing (only if we have magic)
            if HAS_MAGIC and declared_mime and declared_mime != detected_mime:
                logger.warning(
                    f"MIME type mismatch for file {file.name}: "
                    f"declared={declared_mime}, detected={detected_mime}"
                )
                # Allow if detected type is in allowed types
                if detected_mime not in self.allowed_types:
                    raise ValidationError("File type validation failed. Possible file type spoofing.")
        
        except Exception as e:
            logger.error(f"MIME type validation error for file {file.name}: {str(e)}")
            raise ValidationError("Unable to validate file type. Please try again.")
    
    def _validate_file_content(self, file):
        """Validate file content based on type."""
        file.seek(0)
        
        try:
            # Get detected MIME type
            chunk = file.read(1024)
            file.seek(0)
            
            if HAS_MAGIC:
                detected_mime = magic.from_buffer(chunk, mime=True)
            else:
                detected_mime, _ = mimetypes.guess_type(file.name)
                if not detected_mime:
                    # Basic detection from file headers
                    if chunk.startswith(b'\xff\xd8\xff'):
                        detected_mime = 'image/jpeg'
                    elif chunk.startswith(b'\x89PNG'):
                        detected_mime = 'image/png'
                    elif chunk.startswith(b'%PDF'):
                        detected_mime = 'application/pdf'
                    else:
                        detected_mime = 'application/octet-stream'
            
            if detected_mime and detected_mime.startswith('image/'):
                self._validate_image_content(file)
            elif detected_mime == 'application/pdf':
                self._validate_pdf_content(file)
            
        except Exception as e:
            logger.error(f"Content validation error for file {file.name}: {str(e)}")
            raise ValidationError("File content validation failed.")
    
    def _validate_image_content(self, file):
        """Validate image file content and properties."""
        try:
            file.seek(0)
            image = Image.open(file)
            
            # Verify image can be processed
            image.verify()
            
            # Check image dimensions (prevent extremely large images)
            file.seek(0)
            image = Image.open(file)
            width, height = image.size
            
            max_dimension = 10000  # 10k pixels max
            if width > max_dimension or height > max_dimension:
                raise ValidationError(
                    f"Image dimensions ({width}x{height}) exceed maximum allowed size ({max_dimension}x{max_dimension})."
                )
            
            # Check for suspicious metadata
            if hasattr(image, '_getexif') and image._getexif():
                exif = image._getexif()
                # Remove potentially dangerous EXIF data
                if exif:
                    logger.info(f"Image {file.name} contains EXIF data - will be stripped during processing")
        
        except Exception as e:
            raise ValidationError(f"Invalid image file: {str(e)}")
        finally:
            file.seek(0)
    
    def _validate_pdf_content(self, file):
        """Basic PDF content validation."""
        file.seek(0)
        header = file.read(8)
        file.seek(0)
        
        # Check PDF header
        if not header.startswith(b'%PDF-'):
            raise ValidationError("Invalid PDF file format.")
    
    def _security_scan(self, file):
        """Perform security scanning on uploaded file."""
        file.seek(0)
        
        # Read file content for scanning
        content = file.read()
        file.seek(0)
        
        # Check for malicious signatures
        for signature in MALICIOUS_SIGNATURES:
            if signature in content[:1024]:  # Check first 1KB
                logger.warning(f"Suspicious file signature detected in {file.name}")
                raise ValidationError("File contains suspicious content and cannot be uploaded.")
        
        # Calculate file hash for logging/tracking
        file_hash = hashlib.sha256(content).hexdigest()
        logger.info(f"File upload security scan passed: {file.name} (SHA256: {file_hash[:16]}...)")
        
        # Additional security checks can be added here
        # - Virus scanning integration
        # - Content analysis
        # - Reputation checking


@deconstructible
class ImageUploadValidator(FileUploadValidator):
    """Specialized validator for image uploads."""
    
    def __init__(self, max_size=MAX_IMAGE_SIZE):
        super().__init__(
            allowed_types=ALLOWED_IMAGE_TYPES,
            max_size=max_size,
            check_content=True
        )


@deconstructible
class DocumentUploadValidator(FileUploadValidator):
    """Specialized validator for document uploads."""
    
    def __init__(self, max_size=MAX_DOCUMENT_SIZE):
        super().__init__(
            allowed_types=ALLOWED_DOCUMENT_TYPES,
            max_size=max_size,
            check_content=True
        )


@deconstructible
class AttachmentUploadValidator(FileUploadValidator):
    """Specialized validator for message attachments (images + documents)."""
    
    def __init__(self, max_size=MAX_DOCUMENT_SIZE):
        allowed_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_DOCUMENT_TYPES}
        super().__init__(
            allowed_types=allowed_types,
            max_size=max_size,
            check_content=True
        )


def sanitize_filename(filename):
    """
    Sanitize uploaded filename to prevent directory traversal and other attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for storage
    """
    if not filename:
        return 'unnamed_file'
    
    # Remove directory path components
    filename = os.path.basename(filename)
    
    # Remove or replace dangerous characters
    dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit filename length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    # Ensure we have an extension
    if not ext:
        ext = '.txt'
    
    sanitized = f"{name}{ext}"
    
    # Ensure filename is not empty after sanitization
    if not sanitized or sanitized == ext:
        sanitized = f"file_{hashlib.md5(filename.encode()).hexdigest()[:8]}{ext}"
    
    return sanitized


def get_upload_path(instance, filename):
    """
    Generate secure upload path for files.
    
    Args:
        instance: Model instance
        filename: Original filename
        
    Returns:
        Secure upload path
    """
    # Sanitize filename
    safe_filename = sanitize_filename(filename)
    
    # Create date-based directory structure
    from datetime import datetime
    now = datetime.now()
    date_path = now.strftime('%Y/%m/%d')
    
    # Add user ID for organization
    user_id = getattr(instance, 'user_id', 'unknown')
    
    # Generate unique filename to prevent conflicts
    name, ext = os.path.splitext(safe_filename)
    unique_filename = f"{name}_{now.strftime('%H%M%S')}_{hashlib.md5(safe_filename.encode()).hexdigest()[:8]}{ext}"
    
    return f"uploads/{date_path}/{user_id}/{unique_filename}"