import os
from google.cloud import storage

BUCKET_NAME = 'chitchatfiles'

def get_key_path():
    # Calculate path to gcs_key.json in project root
    # This file is in chat-distributed/publisher/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    key_path = os.path.join(project_root, 'gcs_key.json')
    return key_path

def upload_to_gcs(file_obj, filename, content_type):
    key_path = get_key_path()

    if os.path.exists(key_path):
        client = storage.Client.from_service_account_json(key_path)
    else:
        # Fallback to default if key not found (or for testing locally without key)
        print(f"Warning: {key_path} not found. Using default credentials or failing.")
        client = storage.Client()

    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)

    # Ensure file pointer is at start
    file_obj.seek(0)

    blob.upload_from_file(file_obj, content_type=content_type)

    try:
        blob.make_public()
    except Exception as e:
        print(f"Warning: make_public failed: {e}")

    return blob.public_url
