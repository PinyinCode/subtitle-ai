#!/usr/bin/env python3
"""
Xóa file trên Google Drive - DÙNG OAUTH 2.0 REFRESH TOKEN
"""

import os
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def delete_file_with_oauth(file_id, client_id, client_secret, refresh_token):
    """
    Xóa file trên Google Drive sử dụng OAuth 2.0 Refresh Token
    """
    try:
        # Tạo credentials từ refresh token
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri='https://oauth2.googleapis.com/token'
        )
        
        # Refresh để lấy access token mới
        creds.refresh(Request())
        
        # Tạo service
        service = build('drive', 'v3', credentials=creds)
        
        # Xóa file
        print(f"🗑️ Deleting file: {file_id}")
        service.files().delete(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()
        
        print(f"✅ File {file_id} deleted successfully!")
        return True
        
    except HttpError as error:
        if error.resp.status == 404:
            print(f"⚠️ File {file_id} not found (already deleted)")
            return True
        
        print(f"❌ Google API error: {error}")
        if hasattr(error, 'resp') and error.resp.status == 401:
            print("   💡 Token đã hết hạn hoặc không hợp lệ. Vui lòng kiểm tra OAuth credentials.")
        return False
        
    except Exception as error:
        print(f"❌ Unexpected error: {error}")
        return False


def main():
    # Đọc từ environment variables
    file_id = os.getenv('DRIVE_FILE_ID')
    client_id = os.getenv('OAUTH_CLIENT_ID')
    client_secret = os.getenv('OAUTH_CLIENT_SECRET')
    refresh_token = os.getenv('OAUTH_REFRESH_TOKEN')
    
    # Kiểm tra file_id
    if not file_id:
        print("❌ DRIVE_FILE_ID environment variable is required")
        print("💡 Đảm bảo workflow gửi DRIVE_FILE_ID từ client_payload")
        sys.exit(1)
    
    # Kiểm tra OAuth credentials
    if not all([client_id, client_secret, refresh_token]):
        print("❌ Missing OAuth credentials")
        print("   Cần cấu hình các secrets:")
        print("   - OAUTH_CLIENT_ID")
        print("   - OAUTH_CLIENT_SECRET")
        print("   - OAUTH_REFRESH_TOKEN")
        print("💡 Vào Settings → Secrets and variables → Actions để thêm")
        sys.exit(1)
    
    print(f"🗑️ Deleting file: {file_id}")
    print("🔐 Using OAuth 2.0 authentication...")
    
    success = delete_file_with_oauth(file_id, client_id, client_secret, refresh_token)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
