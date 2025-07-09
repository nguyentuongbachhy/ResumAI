import requests
import base64
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class VinternAPIClient:
    def __init__(self, base_url: str = None):
        if base_url is None:
            base_url = os.getenv("VINTERN_API_URL", "https://8000-01jzb2dp011mzm092e3nns9k0m.cloudspaces.litng.ai")
        
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test connection to Vintern API"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("Successfully connected to Vintern API")
                return True
            else:
                logger.warning(f"API health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to Vintern API: {e}")
            return False
    
    def extract_cv_from_file(self, file_path: str, question: str = None) -> str:
        """Extract CV information from file using upload_extract_cv endpoint"""
        try:
            # Prepare the file with correct content type
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            # Determine content type based on file extension
            file_ext = Path(file_path).suffix.lower()
            content_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg', 
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.tiff': 'image/tiff',
                '.pdf': 'application/pdf'
            }.get(file_ext, 'application/octet-stream')
            
            files = {'file': (Path(file_path).name, file_content, content_type)}
            
            # Prepare data
            data = {}
            if question:
                data['question'] = question
            
            # Remove Content-Type header for file upload
            headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
            
            # Make request
            response = self.session.post(
                f"{self.base_url}/upload_extract_cv",
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"API response: {result}")
                
                # Handle different response formats
                extracted_info = result.get('extracted_info', result.get('result', result.get('text', '')))
                
                if not extracted_info and isinstance(result, dict):
                    # Try to find any text content in response
                    for key, value in result.items():
                        if isinstance(value, str) and value.strip():
                            extracted_info = value
                            break
                
                return extracted_info or "No content extracted"
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return f"Error: API request failed with status {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error extracting CV from file: {e}")
            return f"Error: {str(e)}"
    
    def extract_cv_from_base64(self, base64_image: str, question: str = None) -> str:
        """Extract CV information from base64 image using extract_cv endpoint"""
        try:
            payload = {
                'image': base64_image
            }
            
            if question:
                payload['question'] = question
            
            response = self.session.post(
                f"{self.base_url}/extract_cv",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('extracted_info', '')
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return f"Error: API request failed with status {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error extracting CV from base64: {e}")
            return f"Error: {str(e)}"
    
    def extract_from_file(self, file_path: str, question: str = None) -> str:
        """Extract general information from file using upload_extract endpoint"""
        try:
            # Prepare the file with correct content type
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            # Determine content type based on file extension
            file_ext = Path(file_path).suffix.lower()
            content_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg', 
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.tiff': 'image/tiff',
                '.pdf': 'application/pdf'
            }.get(file_ext, 'application/octet-stream')
            
            files = {'file': (Path(file_path).name, file_content, content_type)}
            
            data = {}
            if question:
                data['question'] = question
            
            # Remove Content-Type header for file upload
            headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
            
            response = self.session.post(
                f"{self.base_url}/upload_extract",
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"API response: {result}")
                
                # Handle different response formats
                extracted_info = result.get('extracted_info', result.get('result', result.get('text', '')))
                
                if not extracted_info and isinstance(result, dict):
                    # Try to find any text content in response
                    for key, value in result.items():
                        if isinstance(value, str) and value.strip():
                            extracted_info = value
                            break
                
                return extracted_info or "No content extracted"
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return f"Error: API request failed with status {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error extracting from file: {e}")
            return f"Error: {str(e)}"
    
    def batch_extract_cv(self, image_paths: list, question: str = None) -> Dict[str, str]:
        """Batch extract CV information from multiple images"""
        try:
            # Convert images to base64
            images = []
            for path in image_paths:
                with open(path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                    images.append({
                        'filename': Path(path).name,
                        'image': image_data
                    })
            
            payload = {
                'images': images
            }
            
            if question:
                payload['question'] = question
            
            response = self.session.post(
                f"{self.base_url}/batch_extract",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, dict):
                    # If response is a dict with results key
                    if 'results' in result:
                        return result['results']
                    # If response is direct mapping
                    elif all(isinstance(v, str) for v in result.values()):
                        return result
                    else:
                        # Try to extract from each result
                        results = {}
                        for key, value in result.items():
                            if isinstance(value, dict):
                                results[key] = value.get('extracted_info', value.get('result', str(value)))
                            else:
                                results[key] = str(value)
                        return results
                elif isinstance(result, list):
                    # If response is a list of results
                    results = {}
                    for item in result:
                        if isinstance(item, dict):
                            filename = item.get('filename', f'result_{len(results)}')
                            extracted_info = item.get('extracted_info', item.get('result', str(item)))
                            results[filename] = extracted_info
                    return results
                else:
                    logger.error(f"Unexpected batch response format: {type(result)}")
                    return {}
                    
            else:
                logger.error(f"Batch API request failed: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error in batch extraction: {e}")
            return {}
    
    def get_api_info(self) -> Dict[str, Any]:
        """Get API information"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {}
        except Exception as e:
            logger.error(f"Error getting API info: {e}")
            return {}
    
    def image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64 string"""
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return ""


class VinternProcessor:
    """Compatibility wrapper for existing code"""
    def __init__(self, api_url: str = None):
        if api_url is None:
            api_url = os.getenv("VINTERN_API_URL", "https://8000-01jzb2dp011mzm092e3nns9k0m.cloudspaces.litng.ai")
        
        self.api_client = VinternAPIClient(api_url)
        logger.info(f"VinternProcessor initialized with API client: {api_url}")
    
    def extract_info(self, image_path: str, question: str = None, max_new_tokens: int = 2048) -> str:
        """Extract information from image - compatibility method"""
        # Use CV-specific extraction for better results
        return self.api_client.extract_cv_from_file(image_path, question)
    
    def batch_extract(self, image_paths: list, question: str = None) -> Dict[str, str]:
        """Batch extract information from multiple images"""
        return self.api_client.batch_extract_cv(image_paths, question)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return self.api_client.get_api_info()


# Global instance
vintern_processor = VinternProcessor()
