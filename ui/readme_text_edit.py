"""
Custom QTextEdit widget that supports image loading for README display
"""

from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import QUrl, QTimer, QEventLoop, QByteArray
from PyQt6.QtGui import QTextDocument, QDesktopServices, QImage, QPixmap
from PyQt6.QtNetwork import QNetworkRequest, QNetworkReply
import logging
import re
import base64

logger = logging.getLogger(__name__)


class ReadmeTextEdit(QTextEdit):
    """Custom QTextEdit that properly handles images in README content"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.processed_images = {}
        
        # Enable external resource loading
        self.document().setDocumentMargin(0)
        
        # Set up network manager for image loading
        from PyQt6.QtNetwork import QNetworkAccessManager
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._image_loaded)
    
    def setReadmeContent(self, html_content):
        """Set README content with proper image handling"""
        # Process images to download and embed them
        self.processed_html = self._process_and_download_images(html_content)
        
        # Set the processed HTML
        self.setHtml(self.processed_html)
        
        # Set a timer to clean up failed image loads after a timeout
        QTimer.singleShot(10000, self._cleanup_failed_images)  # 10 seconds timeout
    
    def _process_and_download_images(self, html_content):
        """Process HTML content to download and embed images"""
        import re
        
        # Find all image tags
        img_pattern = r'<img[^>]*src="([^"]*)"[^>]*>'
        
        def replace_img_tag(match):
            img_tag = match.group(0)
            src = match.group(1)
            
            # Skip if already processed or is data URL
            if src.startswith('data:') or src in self.processed_images:
                return img_tag
            
            # Only process external images
            if src.startswith(('http://', 'https://')):
                # Check if this is a GIF
                is_gif = src.lower().endswith('.gif')
                
                # Start download
                self._download_image(src)
                
                # Replace with appropriate placeholder that includes original URL for later replacement
                placeholder_id = f"img_placeholder_{len(self.processed_images)}"
                self.processed_images[placeholder_id] = src  # Store original URL
                
                placeholder = self._get_placeholder_svg(is_gif, placeholder_id)
                return img_tag.replace(
                    src,
                    f'data:image/svg+xml;base64,{placeholder}'
                )
            
            return img_tag
        
        # Process all image tags
        processed_html = re.sub(img_pattern, replace_img_tag, html_content, flags=re.IGNORECASE)
        
        return processed_html
    
    def _download_image(self, url):
        """Download an image from URL"""
        try:
            request = QNetworkRequest(QUrl(url))
            request.setRawHeader(b'User-Agent', b'KOReader-Store/1.0')
            reply = self.network_manager.get(request)
            reply.setProperty('image_url', url)
        except Exception as e:
            logger.error(f"Failed to download image {url}: {e}")
    
    def _image_loaded(self, reply):
        """Handle downloaded image"""
        try:
            if reply.error() == reply.NetworkError.NoError:
                image_url = reply.property('image_url')
                image_data = reply.readAll()
                
                # Convert to base64 data URL
                mime_type = self._get_mime_type(image_url)
                base64_data = base64.b64encode(image_data).decode('utf-8')
                data_url = f'data:{mime_type};base64,{base64_data}'
                
                # Special handling for animated GIFs
                if mime_type == 'image/gif' and self._is_animated_gif(image_data):
                    # Add animation indicator for GIFs
                    data_url = self._add_gif_animation_indicator(data_url)
                
                # Store processed image with original URL as key
                self.processed_images[image_url] = data_url
                
                # Update HTML to replace placeholder with actual image
                self._update_image_in_html(image_url, data_url)
                
            else:
                logger.error(f"Failed to load image: {reply.errorString()}")
                # Mark as failed to avoid infinite loading
                image_url = reply.property('image_url')
                self.processed_images[image_url] = "FAILED"
                
        except Exception as e:
            logger.error(f"Error processing downloaded image: {e}")
            image_url = reply.property('image_url')
            self.processed_images[image_url] = "FAILED"
        finally:
            reply.deleteLater()
    
    def _is_animated_gif(self, image_data):
        """Check if GIF data contains animation"""
        try:
            # Convert QByteArray to bytes for analysis
            gif_bytes = bytes(image_data)
            
            # Simple check for animated GIF by looking for multiple image descriptors
            # GIF files have image descriptors that start with 0x2C (comma)
            image_descriptors = gif_bytes.count(b'\x2C')
            
            # If more than one image descriptor, it's likely animated
            return image_descriptors > 1
            
        except Exception as e:
            logger.debug(f"Error checking GIF animation: {e}")
            return False
    
    def _add_gif_animation_indicator(self, data_url):
        """Add visual indicator for animated GIFs"""
        # Wrap the GIF in a container with animation indicator
        return f'''
        <div style="position: relative; display: inline-block;">
            <img src="{data_url}" style="max-width: 100%; height: auto; border-radius: 8px;" />
            <div style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-family: Arial;">
                GIF
            </div>
        </div>
        '''
    
    def _update_image_in_html(self, original_url, data_url):
        """Update HTML to replace image URL with data URL"""
        try:
            current_html = self.toHtml()
            
            # Find and replace the image URL in the HTML
            # Look for the placeholder or original URL
            updated_html = current_html.replace(original_url, data_url)
            
            # Also replace any placeholder data URLs that contain the original URL
            import re
            placeholder_pattern = rf'data:image/svg\+xml;base64,([^"]*{re.escape(original_url)}[^"]*)'
            updated_html = re.sub(placeholder_pattern, data_url, updated_html)
            
            # Update the document
            self.setHtml(updated_html)
            
        except Exception as e:
            logger.error(f"Error updating HTML with image: {e}")
    
    def _get_mime_type(self, url):
        """Get MIME type from URL"""
        url_lower = url.lower()
        if url_lower.endswith('.png'):
            return 'image/png'
        elif url_lower.endswith('.jpg') or url_lower.endswith('.jpeg'):
            return 'image/jpeg'
        elif url_lower.endswith('.gif'):
            return 'image/gif'
        elif url_lower.endswith('.svg'):
            return 'image/svg+xml'
        elif url_lower.endswith('.webp'):
            return 'image/webp'
        elif url_lower.endswith('.bmp'):
            return 'image/bmp'
        else:
            return 'image/png'  # Default
    
    def _get_placeholder_svg(self, is_gif=False, placeholder_id=None):
        """Get a simple placeholder SVG as base64"""
        if is_gif:
            text = "Loading GIF..."
            color = "#10b981"  # Green for GIFs
        else:
            text = "Loading image..."
            color = "#6b7280"  # Gray for regular images
            
        svg = f'''
        <svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#f3f4f6"/>
            <text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="{color}" font-family="Arial" font-size="12">
                {text}
            </text>
        </svg>
        '''
        return base64.b64encode(svg.encode()).decode()
    
    def _cleanup_failed_images(self):
        """Clean up failed image loads by removing broken placeholders"""
        try:
            current_html = self.toHtml()
            
            # Remove any remaining loading placeholders for failed images
            import re
            failed_pattern = r'data:image/svg\+xml;base64,[^"]*(?:Loading image|Loading GIF)[^"]*'
            cleaned_html = re.sub(failed_pattern, '', current_html)
            
            # Also remove empty img tags that might result from failed loads
            empty_img_pattern = r'<img[^>]*src=""[^>]*>'
            cleaned_html = re.sub(empty_img_pattern, '', cleaned_html)
            
            if cleaned_html != current_html:
                self.setHtml(cleaned_html)
                logger.info("Cleaned up failed image placeholders")
                
        except Exception as e:
            logger.error(f"Error cleaning up failed images: {e}")
