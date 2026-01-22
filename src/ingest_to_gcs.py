import io
import os
import zipfile

import requests
from google.cloud import storage

project_id = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
BASE_URL = "https://s3.amazonaws.com/tripdata"


# GCS client
storage_client = storage.Client(project=project_id)
bucket = storage_client.bucket(BUCKET_NAME)


def upload_zip_content_to_gcs(year, month):
    file_name = f"{year}{month:02d}-citibike-tripdata.zip"
    url = f"{BASE_URL}/{file_name}"

    print(f"Downloading {file_name} into memory...")

    # download file (streaming)
    response = requests.get(url)

    if response.status_code == 200:
        # unzip on memory
        z = zipfile.ZipFile(io.BytesIO(response.content))

        for name in z.namelist():
            if name.endswith(".csv") and not name.startswith("__MACOSX"):
                print(f" -> Extracting & Uploading: {name}")

                # save file to GCS
                blob = bucket.blob(f"raw_data/{name}")

                # Upload directly from memory
                blob.upload_from_string(z.read(name), content_type="text/csv")
                print(f" -> Upload Complete: gs://{BUCKET_NAME}/raw_data/{name}")
    else:
        print(f"Failed to download {url}")


if __name__ == "__main__":
    for i in range(1, 13):
        upload_zip_content_to_gcs(2024, i)

    for i in range(1, 13):
        upload_zip_content_to_gcs(2025, i)
