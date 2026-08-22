#!/usr/bin/env python3
"""
Xóa file trên Google Drive - SỬA SCOPE
"""

import os
import json
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def delete_file(file_id, service_account_key):
    try:
        if isinstance(service_account_key, str):
            service_account_info = json.loads(service_account_key)
        else:
            service_account_info = service_account_key
        
        # ✅ SỬA SCOPE
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive']  # ĐÃ SỬA
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        # ✅ XÓA THẬT
        service.files().delete(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()
        
        print(f"✅ Successfully deleted file: {file_id}")
        return True
        
    except HttpError as error:
        if error.resp.status == 404:
            print(f"⚠️ File {file_id} not found (already deleted)")
            return True
        print(f"❌ Google API error: {error}")
        return False
    except Exception as error:
        print(f"❌ Error: {error}")
        return False

def main():
    file_id = os.getenv('DRIVE_FILE_ID')
    service_account_key = os.getenv('DRIVE_SERVICE_ACCOUNT_KEY')
    
    if not file_id:
        print("❌ DRIVE_FILE_ID environment variable is required")
        sys.exit(1)
    
    if not service_account_key:
        print("❌ DRIVE_SERVICE_ACCOUNT_KEY environment variable is required")
        sys.exit(1)
    
    print(f"🗑️ Deleting file: {file_id}")
    success = delete_file(file_id, service_account_key)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
