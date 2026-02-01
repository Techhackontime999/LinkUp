"""
Static file optimization utilities for improved performance.
Implements compression, minification, and caching strategies.
"""

import os
import gzip
import hashlib
import logging
from django.conf import settings
from django.contrib.staticfiles.storage import StaticFilesStorage
from django.core.files.base import ContentFile
from django.utils.encoding import force_bytes

logger = logging.getLogger(__name__)


class OptimizedStaticFilesStorage(StaticFilesStorage):
    """
    Enhanced static files storage with compression and optimization.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compressed_files = {}
    
    def post_process(self, paths, dry_run=False, **options):
        """
        Post-process static files with compression and optimization.
        """
        if dry_run:
            return
        
        # Process files for compression
        for original_path, processed_path, processed in super().post_process(paths, dry_run, **options):
            if processed:
                # Compress CSS and JS files
                if self._should_compress(processed_path):
                    self._compress_file(processed_path)
                
                # Generate file hashes for cache busting
                self._generate_file_hash(processed_path)
            
            yield original_path, processed_path, processed
    
    def _should_compress(self, path):
        """Check if file should be compressed."""
        compressible_extensions = ['.css', '.js', '.html', '.svg', '.json']
        return any(path.endswith(ext) for ext in compressible_extensions)
    
    def _compress_file(self, path):
        """Compress file using gzip."""
        try:
            full_path = self.path(path)
            
            if not os.path.exists(full_path):
                return
            
            # Read original file
            with open(full_path, 'rb') as f:
                content = f.read()
            
            # Compress content
            compressed_content = gzip.compress(content)
            
            # Save compressed version
            compressed_path = f"{full_path}.gz"
            with open(compressed_path, 'wb') as f:
                f.write(compressed_content)
            
            # Store compression info
            self.compressed_files[path] = {
                'original_size': len(content),
                'compressed_size': len(compressed_content),
                'compression_ratio': len(compressed_content) / len(content)
            }
            
            logger.info(f"Compressed {path}: {len(content)} -> {len(compressed_content)} bytes")
            
        except Exception as e:
            logger.error(f"Error compressing {path}: {e}")
    
    def _generate_file_hash(self, path):
        """Generate hash for cache busting."""
        try:
            full_path = self.path(path)
            
            if not os.path.exists(full_path):
                return
            
            with open(full_path, 'rb') as f:
                content = f.read()
            
            file_hash = hashlib.md5(content).hexdigest()[:8]
            
            # Store hash for later use
            if not hasattr(self, 'file_hashes'):
                self.file_hashes = {}
            
            self.file_hashes[path] = file_hash
            
        except Exception as e:
            logger.error(f"Error generating hash for {path}: {e}")


class CSSOptimizer:
    """
    CSS optimization utilities.
    """
    
    @staticmethod
    def minify_css(css_content):
        """
        Basic CSS minification.
        """
        import re
        
        # Remove comments
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Remove extra whitespace
        css_content = re.sub(r'\s+', ' ', css_content)
        
        # Remove whitespace around specific characters
        css_content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', css_content)
        
        # Remove trailing semicolons
        css_content = re.sub(r';}', '}', css_content)
        
        return css_content.strip()
    
    @staticmethod
    def optimize_css_file(file_path):
        """
        Optimize a CSS file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            optimized_content = CSSOptimizer.minify_css(content)
            
            # Save optimized version
            optimized_path = file_path.replace('.css', '.min.css')
            with open(optimized_path, 'w', encoding='utf-8') as f:
                f.write(optimized_content)
            
            logger.info(f"Optimized CSS: {file_path} -> {optimized_path}")
            
            return optimized_path
            
        except Exception as e:
            logger.error(f"Error optimizing CSS file {file_path}: {e}")
            return file_path


class JSOptimizer:
    """
    JavaScript optimization utilities.
    """
    
    @staticmethod
    def minify_js(js_content):
        """
        Basic JavaScript minification.
        """
        import re
        
        # Remove single-line comments (but preserve URLs)
        js_content = re.sub(r'(?<!:)//.*$', '', js_content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        
        # Remove extra whitespace
        js_content = re.sub(r'\s+', ' ', js_content)
        
        # Remove whitespace around operators
        js_content = re.sub(r'\s*([{}();,=+\-*/<>!&|])\s*', r'\1', js_content)
        
        return js_content.strip()
    
    @staticmethod
    def optimize_js_file(file_path):
        """
        Optimize a JavaScript file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            optimized_content = JSOptimizer.minify_js(content)
            
            # Save optimized version
            optimized_path = file_path.replace('.js', '.min.js')
            with open(optimized_path, 'w', encoding='utf-8') as f:
                f.write(optimized_content)
            
            logger.info(f"Optimized JS: {file_path} -> {optimized_path}")
            
            return optimized_path
            
        except Exception as e:
            logger.error(f"Error optimizing JS file {file_path}: {e}")
            return file_path


class ImageOptimizer:
    """
    Image optimization utilities.
    """
    
    @staticmethod
    def optimize_image(image_path, quality=85):
        """
        Optimize image file size while maintaining quality.
        """
        try:
            from PIL import Image
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Optimize and save
                optimized_path = image_path.replace('.jpg', '_optimized.jpg').replace('.png', '_optimized.jpg')
                img.save(optimized_path, 'JPEG', quality=quality, optimize=True)
                
                # Get file sizes
                original_size = os.path.getsize(image_path)
                optimized_size = os.path.getsize(optimized_path)
                
                logger.info(
                    f"Optimized image: {image_path} "
                    f"({original_size} -> {optimized_size} bytes, "
                    f"{(1 - optimized_size/original_size)*100:.1f}% reduction)"
                )
                
                return optimized_path
                
        except Exception as e:
            logger.error(f"Error optimizing image {image_path}: {e}")
            return image_path


def optimize_static_files():
    """
    Optimize all static files in the project.
    """
    if not settings.DEBUG:
        logger.warning("Static file optimization should be run in production mode")
        return
    
    static_root = settings.STATIC_ROOT
    if not static_root or not os.path.exists(static_root):
        logger.error("STATIC_ROOT not found. Run collectstatic first.")
        return
    
    optimized_count = 0
    
    # Walk through static files
    for root, dirs, files in os.walk(static_root):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip already optimized files
            if '.min.' in file or '_optimized.' in file:
                continue
            
            try:
                if file.endswith('.css'):
                    CSSOptimizer.optimize_css_file(file_path)
                    optimized_count += 1
                elif file.endswith('.js'):
                    JSOptimizer.optimize_js_file(file_path)
                    optimized_count += 1
                elif file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    ImageOptimizer.optimize_image(file_path)
                    optimized_count += 1
                    
            except Exception as e:
                logger.error(f"Error optimizing {file_path}: {e}")
    
    logger.info(f"Optimized {optimized_count} static files")


def generate_cache_manifest():
    """
    Generate cache manifest for static files.
    """
    static_root = settings.STATIC_ROOT
    if not static_root or not os.path.exists(static_root):
        return
    
    manifest = {
        'files': {},
        'version': hashlib.md5(str(os.path.getmtime(static_root)).encode()).hexdigest()[:8]
    }
    
    # Generate file hashes for cache busting
    for root, dirs, files in os.walk(static_root):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, static_root)
            
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                file_hash = hashlib.md5(content).hexdigest()[:8]
                manifest['files'][relative_path] = {
                    'hash': file_hash,
                    'size': len(content),
                    'url': f"{settings.STATIC_URL}{relative_path}?v={file_hash}"
                }
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
    
    # Save manifest
    manifest_path = os.path.join(static_root, 'cache_manifest.json')
    import json
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"Generated cache manifest with {len(manifest['files'])} files")
    return manifest