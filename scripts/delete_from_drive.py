#!/usr/bin/env python3
"""
Xóa file trên Google Drive với retry, logging và xử lý lỗi nâng cao
"""

import os
import json
import sys
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DriveManager:
    """Quản lý thao tác với Google Drive"""
    
    def __init__(self, service_account_key: Dict[str, Any]):
        """
        Khởi tạo Drive Manager
        
        Args:
            service_account_key: JSON key của service account
        """
        self.creds = Credentials.from_service_account_info(
            service_account_key,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        self.service = build('drive', 'v3', credentials=self.creds)
    
    def delete_file(self, file_id: str, retry_count: int = 3) -> bool:
        """
        Xóa file với retry và exponential backoff
        
        Args:
            file_id: ID của file cần xóa
            retry_count: Số lần thử lại
        
        Returns:
            bool: True nếu xóa thành công
        """
        for attempt in range(retry_count):
            try:
                logger.info(f"🗑️ Deleting file: {file_id} (attempt {attempt + 1}/{retry_count})")
                
                # Gọi API delete
                self.service.files().delete(fileId=file_id).execute()
                
                logger.info(f"✅ Successfully deleted file: {file_id}")
                return True
                
            except HttpError as error:
                error_code = error.resp.status
                error_msg = error._get_reason()
                
                if error_code == 404:
                    logger.warning(f"⚠️ File {file_id} not found (already deleted)")
                    return True  # File không tồn tại coi như đã xóa
                
                if error_code == 403:
                    logger.error(f"🚫 Permission denied: {error_msg}")
                    logger.error("   Check:")
                    logger.error("   - Service account has access to the file/folder")
                    logger.error("   - File/folder is shared with service account email")
                    logger.error("   - Service account has Editor/Manager role")
                    return False
                
                if error_code == 429:  # Rate limit
                    if attempt < retry_count - 1:
                        wait_time = 2 ** (attempt + 1)  # 2, 4, 8 seconds
                        logger.warning(f"⏳ Rate limit reached, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed after {retry_count} attempts: {error_msg}")
                    
            except Exception as error:
                logger.error(f"❌ Unexpected error: {error}")
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        
        return False
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin file
        
        Args:
            file_id: ID của file
        
        Returns:
            Dict: Thông tin file hoặc None nếu không tìm thấy
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,size,createdTime,modifiedTime,owners'
            ).execute()
            
            logger.info(f"📄 File info: {file.get('name')} ({file.get('mimeType')})")
            return file
            
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"⚠️ File {file_id} not found")
            else:
                logger.error(f"❌ Error getting file info: {error}")
            return None
    
    def move_to_trash(self, file_id: str) -> bool:
        """
        Di chuyển file vào Trash thay vì xóa vĩnh viễn
        
        Args:
            file_id: ID của file
        
        Returns:
            bool: True nếu thành công
        """
        try:
            self.service.files().update(
                fileId=file_id,
                body={'trashed': True}
            ).execute()
            
            logger.info(f"♻️ Moved file {file_id} to trash")
            return True
            
        except HttpError as error:
            logger.error(f"❌ Failed to move to trash: {error}")
            return False

def main():
    """Main function"""
    # Lấy environment variables
    file_id = os.getenv('DRIVE_FILE_ID')
    service_account_key_str = os.getenv('DRIVE_SERVICE_ACCOUNT_KEY')
    delete_mode = os.getenv('DELETE_MODE', 'permanent')  # permanent | trash
    
    # Kiểm tra required variables
    if not file_id:
        logger.error("❌ DRIVE_FILE_ID environment variable is required")
        sys.exit(1)
    
    if not service_account_key_str:
        logger.error("❌ DRIVE_SERVICE_ACCOUNT_KEY environment variable is required")
        logger.info("💡 Add it to GitHub Secrets: Settings → Secrets → Actions")
        sys.exit(1)
    
    # Parse service account key
    try:
        service_account_key = json.loads(service_account_key_str)
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in DRIVE_SERVICE_ACCOUNT_KEY")
        sys.exit(1)
    
    # Khởi tạo Drive Manager
    drive_manager = DriveManager(service_account_key)
    
    # Lấy thông tin file trước khi xóa
    logger.info("🔍 Getting file info...")
    file_info = drive_manager.get_file_info(file_id)
    
    if not file_info:
        logger.warning("⚠️ File not found, skipping deletion")
        sys.exit(0)
    
    logger.info(f"📄 File: {file_info.get('name')} ({file_info.get('size', 0) / 1024:.2f} KB)")
    
    # Xóa file theo mode
    if delete_mode == 'trash':
        logger.info("♻️ Moving file to trash...")
        success = drive_manager.move_to_trash(file_id)
    else:
        logger.info("🗑️ Permanently deleting file...")
        success = drive_manager.delete_file(file_id)
    
    if success:
        logger.info("✅ File deletion completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ File deletion failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
