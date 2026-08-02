#!/usr/bin/env python3
"""
Xóa file trên Google Drive - Xóa thực sự (vĩnh viễn)
"""

import os
import json
import sys
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def delete_file_real(file_id, service_account_key, retry_count=3):
    """
    Xóa file thực sự trên Google Drive
    
    Args:
        file_id: ID của file cần xóa
        service_account_key: JSON key của service account
        retry_count: Số lần thử lại
    
    Returns:
        bool: True nếu xóa thành công, False nếu thất bại
    """
    for attempt in range(retry_count):
        try:
            # Parse service account key
            if isinstance(service_account_key, str):
                service_account_info = json.loads(service_account_key)
            else:
                service_account_info = service_account_key
            
            # Tạo credentials với quyền đầy đủ
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/drive']  # 🆕 QUYỀN ĐẦY ĐỦ
            )
            
            # Khởi tạo Drive service
            service = build('drive', 'v3', credentials=creds)
            
            # 🔥 Gọi API DELETE - XÓA THỰC SỰ
            print(f"🗑️ Attempt {attempt + 1}: Deleting file {file_id}...")
            service.files().delete(fileId=file_id).execute()
            
            print(f"✅ Successfully DELETED file: {file_id}")
            return True
            
        except HttpError as error:
            error_code = error.resp.status
            error_msg = error._get_reason()
            
            if error_code == 404:
                print(f"⚠️ File {file_id} not found (may have been deleted already)")
                # ❌ KHÔNG coi là thành công nếu không tìm thấy
                # Vì có thể file chưa tồn tại hoặc đã bị xóa từ trước
                print(f"⚠️ Cannot verify deletion - file not found")
                return False  # 🆕 KHÔNG coi là thành công
                
            if error_code == 403:
                print(f"🚫 PERMISSION DENIED: {error_msg}")
                print(f"📌 Service Account needs EDITOR or MANAGER permission on this file/folder")
                print(f"📌 Check: https://drive.google.com/drive/folders/...")
                print(f"📌 Share with: {service_account_info.get('client_email')}")
                return False
                
            if error_code == 429:  # Rate limit
                if attempt < retry_count - 1:
                    wait_time = 2 ** (attempt + 1)
                    print(f"⏳ Rate limit, retry in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            
            print(f"❌ Error: {error_code} - {error_msg}")
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt
                print(f"⏳ Retry in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return False
                
        except Exception as error:
            print(f"❌ Unexpected error: {error}")
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt
                print(f"⏳ Retry in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return False
    
    return False

def verify_file_deleted(file_id, service_account_key):
    """
    Kiểm tra file đã bị xóa chưa
    """
    try:
        if isinstance(service_account_key, str):
            service_account_info = json.loads(service_account_key)
        else:
            service_account_info = service_account_key
        
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)
        
        # Thử lấy thông tin file
        service.files().get(fileId=file_id).execute()
        return False  # File vẫn tồn tại
        
    except HttpError as error:
        if error.resp.status == 404:
            return True  # File không tồn tại → đã bị xóa
        return False

def main():
    """Main function"""
    file_id = os.getenv('DRIVE_FILE_ID')
    service_account_key = os.getenv('DRIVE_SERVICE_ACCOUNT_KEY')
    
    if not file_id:
        print("❌ DRIVE_FILE_ID environment variable is required")
        sys.exit(1)
    
    if not service_account_key:
        print("❌ DRIVE_SERVICE_ACCOUNT_KEY environment variable is required")
        print("💡 Add it to GitHub Secrets: Settings → Secrets → Actions")
        sys.exit(1)
    
    print(f"🗑️ Starting file deletion: {file_id}")
    print(f"⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Thực hiện xóa
    success = delete_file_real(file_id, service_account_key)
    
    if success:
        print(f"✅ File {file_id} has been permanently deleted from Google Drive")
        sys.exit(0)
    else:
        print(f"❌ Failed to delete file {file_id} after retries")
        print(f"💡 Please check:")
        print(f"   1. Service Account has permission (Editor/Manager)")
        print(f"   2. File exists and is accessible")
        print(f"   3. File ID is correct: {file_id}")
        sys.exit(1)

if __name__ == "__main__":
    main()
