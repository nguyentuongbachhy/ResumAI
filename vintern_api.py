import requests
import base64
import json
import logging
from typing import Dict, Any, Optional, List
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
                '.tif': 'image/tiff',
                '.webp': 'image/webp',
                '.pdf': 'application/pdf'
            }.get(file_ext, 'application/octet-stream')
            
            # Prepare file upload - use 'file' field name for compatibility
            with open(file_path, 'rb') as f:
                files = {
                    'file': (Path(file_path).name, f, content_type)
                }
                
                # Prepare form data
                data = {}
                if question:
                    data['question'] = question
                
                logger.debug(f"Uploading file: {Path(file_path).name}, size: {os.path.getsize(file_path)} bytes")
                
                # Make request to upload_extract_cv endpoint
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
                    
                    # Handle updated response format
                    if result.get('success'):
                        extracted_info = result.get('extracted_info', '')
                        return extracted_info if extracted_info else "No content extracted"
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        return f"Error: {error_msg}"
                        
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
                if result.get('success'):
                    return result.get('extracted_info', 'No content extracted')
                else:
                    return f"Error: {result.get('error', 'Unknown error')}"
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
                '.tif': 'image/tiff',
                '.webp': 'image/webp',
                '.pdf': 'application/pdf'
            }.get(file_ext, 'application/octet-stream')
            
            # Prepare file upload - use 'file' field name
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
                    
                    # Handle updated response format
                    if result.get('success'):
                        extracted_info = result.get('result', '')
                        return extracted_info if extracted_info else "No content extracted"
                    else:
                        return f"Error: {result.get('error', 'Unknown error')}"
                        
                except json.JSONDecodeError:
                    return response.text if response.text.strip() else "No content extracted"
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return f"Error: API request failed with status {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error extracting from file: {e}")
            return f"Error: {str(e)}"
    
    def batch_extract_cv(self, image_paths: List[str], question: str = None) -> Dict[str, str]:
        """Batch extract CV information from multiple images"""
        try:
            # Convert images to base64 with filename mapping
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
                    logger.debug(f"Added image to batch: {Path(path).name}")
                except Exception as e:
                    logger.error(f"Error reading file {path}: {e}")
                    continue
            
            if not images:
                logger.error("No valid images to process")
                return {}
            
            # Default CV extraction question if none provided
            if question is None:
                question = """Trích xuất thông tin chi tiết từ CV này bao gồm:
1. Thông tin cá nhân (tên, email, số điện thoại, địa chỉ)
2. Kinh nghiệm làm việc (công ty, vị trí, thời gian, mô tả công việc)
3. Kỹ năng và chuyên môn
4. Học vấn và bằng cấp
5. Chứng chỉ và khóa học
6. Dự án đã thực hiện
7. Ngôn ngữ lập trình (nếu có)
8. Các thông tin khác liên quan

Trả về dạng markdown có cấu trúc rõ ràng."""
            
            payload = {
                'images': images,
                'question': question
            }
            
            logger.info(f"Sending batch request for {len(images)} images")
            logger.debug(f"Batch payload keys: {list(payload.keys())}")
            
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
                    
                    if result.get('success'):
                        # New format: response contains 'results' with filename mapping
                        batch_results = result.get('results', {})
                        
                        if isinstance(batch_results, dict):
                            logger.info(f"Batch processing successful for {len(batch_results)} images")
                            return batch_results
                        else:
                            logger.error(f"Unexpected batch results format: {type(batch_results)}")
                            return {}
                    else:
                        error_msg = result.get('error', 'Unknown batch processing error')
                        logger.error(f"Batch processing failed: {error_msg}")
                        return {}
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse batch response as JSON: {e}")
                    logger.error(f"Response content: {response.text}")
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
    
    def batch_extract(self, image_paths: List[str], question: str = None) -> Dict[str, str]:
        """Batch extract information from multiple images"""
        try:
            # Try batch API first
            logger.info(f"Attempting batch extraction for {len(image_paths)} images")
            batch_results = self.api_client.batch_extract_cv(image_paths, question)
            
            if batch_results and isinstance(batch_results, dict):
                # Check if we got results for all images
                processed_files = set(batch_results.keys())
                expected_files = {Path(path).name for path in image_paths}
                
                if processed_files == expected_files:
                    logger.info(f"Batch extraction successful for all {len(batch_results)} images")
                    return batch_results
                else:
                    missing_files = expected_files - processed_files
                    logger.warning(f"Batch extraction incomplete. Missing: {missing_files}")
                    
                    # Fill in missing files with individual processing
                    for path in image_paths:
                        filename = Path(path).name
                        if filename not in batch_results:
                            logger.info(f"Processing missing file individually: {filename}")
                            result = self.extract_info(path, question)
                            batch_results[filename] = result
                    
                    return batch_results
            else:
                logger.warning("Batch extraction failed or returned empty results")
                
        except Exception as e:
            logger.error(f"Batch extraction failed: {e}")
        
        # Fallback to individual processing
        logger.info("Falling back to individual processing")
        results = {}
        for path in image_paths:
            try:
                filename = Path(path).name
                logger.info(f"Processing {filename} individually")
                result = self.extract_info(path, question)
                results[filename] = result
            except Exception as e:
                logger.error(f"Error processing {path}: {e}")
                results[Path(path).name] = f"Error: {str(e)}"
                
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return self.api_client.get_api_info()


# Global instance
vintern_processor = VinternProcessor()