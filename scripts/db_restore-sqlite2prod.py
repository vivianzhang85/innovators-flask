#!/usr/bin/env python3

import requests
import json
import os
import time

# Configuration
PROD_AUTH_URL = "https://flask.opencodingsociety.com/api/authenticate"
PROD_DATA_URL = "https://flask.opencodingsociety.com/api/user"  # Usually singular for single user creation
LOCAL_JSON = "instance/data.json"

# Credentials for production server
UID = os.environ.get("DEFAULT_UID") or "user"
PASSWORD = os.environ.get("DEFAULT_USER_PASSWORD") or "password"

def authenticate(uid, password):
    auth_data = {"uid": uid, "password": password}
    headers = {"Content-Type": "application/json"}
    response = requests.post(PROD_AUTH_URL, json=auth_data, headers=headers)
    response.raise_for_status()
    return response.cookies

def read_local_data(json_file):
    with open(json_file, "r") as f:
        return json.load(f)  # This will be a list

def upload_user(user, cookies):
    headers = {"Content-Type": "application/json"}
    response = requests.post(PROD_DATA_URL, json=user, headers=headers, cookies=cookies)
    print(f"User {user.get('uid')}: Status code: {response.status_code}")
    if response.status_code >= 400:
        print(f"Response: {response.text}")

def main():
    # Step 1: Authenticate to production server
    try:
        cookies = authenticate(UID, PASSWORD)
        print("Authenticated to production server.")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # Step 2: Read local data
    try:
        users = read_local_data(LOCAL_JSON)
        print(f"Loaded {len(users)} users from local data.")
    except Exception as e:
        print(f"Failed to read local data: {e}")
        return

    # Step 3: Upload users to production one by one
    for user in users:
        try:
            upload_user(user, cookies)
            time.sleep(0.2)  # Small delay to avoid rate limits
        except Exception as e:
            print(f"Failed to upload user {user.get('uid')}: {e}")

    print("Data upload complete.")

if __name__ == "__main__":
    main()