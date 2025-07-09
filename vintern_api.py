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
        
        # Set default headers for JSON requests only
        self.json_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test connection to Vintern API"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
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
            # Verify file exists
            if not os.path.exists(file_path):
                return f"Error: File not found: {file_path}"
            
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
            
            # Prepare file upload
            with open(file_path, 'rb') as f:
                files = {
                    'file': (Path(file_path).name, f, content_type)
                }
                
                # Prepare form data
                data = {}
                if question:
                    data['question'] = question
                
                logger.debug(f"Uploading file: {Path(file_path).name}, size: {os.path.getsize(file_path)} bytes")
                
                # Make request without Content-Type header (let requests handle multipart)
                response = requests.post(
                    f"{self.base_url}/upload_extract_cv",
                    files=files,
                    data=data,
                    timeout=60
                )
            
            logger.debug(f"API response status: {response.status_code}")
            logger.debug(f"API response content: {response.text[:500]}...")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.debug(f"Parsed API response: {result}")
                    
                    # Handle different response formats
                    extracted_info = result.get('extracted_info', result.get('result', result.get('text', '')))
                    
                    if not extracted_info and isinstance(result, dict):
                        # Try to find any text content in response
                        for key, value in result.items():
                            if isinstance(value, str) and value.strip() and not key.startswith('_'):
                                extracted_info = value
                                break
                    
                    if not extracted_info:
                        extracted_info = "No content extracted from API response"
                        
                    return extracted_info
                except json.JSONDecodeError:
                    # If response is not JSON, return the text content
                    return response.text if response.text.strip() else "No content extracted"
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return f"Error: {error_msg}"
                
        except Exception as e:
            error_msg = f"Error extracting CV from file: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    def extract_cv_from_base64(self, base64_image: str, question: str = None) -> str:
        """Extract CV information from base64 image using extract_cv endpoint"""
        try:
            payload = {
                'image': base64_image
            }
            
            if question:
                payload['question'] = question
            
            response = requests.post(
                f"{self.base_url}/extract_cv",
                json=payload,
                headers=self.json_headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('extracted_info', result.get('result', result.get('text', 'No content extracted')))
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return f"Error: API request failed with status {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error extracting CV from base64: {e}")
            return f"Error: {str(e)}"
    
    def extract_from_file(self, file_path: str, question: str = None) -> str:
        """Extract general information from file using upload_extract endpoint"""
        try:
            # Verify file exists
            if not os.path.exists(file_path):
                return f"Error: File not found: {file_path}"
            
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
            
            # Prepare file upload
            with open(file_path, 'rb') as f:
                files = {
                    'file': (Path(file_path).name, f, content_type)
                }
                
                data = {}
                if question:
                    data['question'] = question
                
                response = requests.post(
                    f"{self.base_url}/upload_extract",
                    files=files,
                    data=data,
                    timeout=60
                )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.debug(f"API response: {result}")
                    
                    # Handle different response formats
                    extracted_info = result.get('extracted_info', result.get('result', result.get('text', '')))
                    
                    if not extracted_info and isinstance(result, dict):
                        # Try to find any text content in response
                        for key, value in result.items():
                            if isinstance(value, str) and value.strip() and not key.startswith('_'):
                                extracted_info = value
                                break
                    
                    return extracted_info or "No content extracted"
                except json.JSONDecodeError:
                    return response.text if response.text.strip() else "No content extracted"
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
                if not os.path.exists(path):
                    logger.warning(f"File not found: {path}")
                    continue
                    
                try:
                    with open(path, 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                        images.append({
                            'filename': Path(path).name,
                            'image': image_data
                        })
                except Exception as e:
                    logger.error(f"Error reading file {path}: {e}")
                    continue
            
            if not images:
                logger.error("No valid images to process")
                return {}
            
            payload = {
                'images': images
            }
            
            if question:
                payload['question'] = question
            
            response = requests.post(
                f"{self.base_url}/batch_extract",
                json=payload,
                headers=self.json_headers,
                timeout=120
            )
            
            logger.debug(f"Batch API response status: {response.status_code}")
            logger.debug(f"Batch API response: {response.text[:1000]}...")
            
            if response.status_code == 200:
                try:
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
                        for i, item in enumerate(result):
                            if isinstance(item, dict):
                                filename = item.get('filename', f'result_{i}')
                                extracted_info = item.get('extracted_info', item.get('result', str(item)))
                                results[filename] = extracted_info
                            else:
                                results[f'result_{i}'] = str(item)
                        return results
                    else:
                        logger.error(f"Unexpected batch response format: {type(result)}")
                        return {}
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse batch response as JSON: {response.text}")
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
            response = requests.get(f"{self.base_url}/", timeout=10)
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
        result = self.api_client.extract_cv_from_file(image_path, question)
        
        # If CV-specific extraction fails, try general extraction
        if result.startswith('Error:'):
            logger.warning(f"CV extraction failed, trying general extraction for {image_path}")
            result = self.api_client.extract_from_file(image_path, question)
        
        return result
    
    def batch_extract(self, image_paths: list, question: str = None) -> Dict[str, str]:
        """Batch extract information from multiple images"""
        try:
            return self.api_client.batch_extract_cv(image_paths, question)
        except Exception as e:
            logger.error(f"Batch extraction failed: {e}")
            # Fallback to individual processing
            results = {}
            for path in image_paths:
                filename = Path(path).name
                result = self.extract_info(path, question)
                results[filename] = result
            return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return self.api_client.get_api_info()


# Global instance
vintern_processor = VinternProcessor()