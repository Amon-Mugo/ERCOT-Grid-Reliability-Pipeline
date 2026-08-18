import json
import time
import boto3
from typing import Any
from botocore.exceptions import ClientError

BUCKET_NAME = "ercot-grid-pipeline-raw"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (20, 30, 40)


class S3LoaderError(Exception):
    pass


def _rows_to_ndjson(rows: list[dict[str, Any]]) -> bytes:

    lines = (json.dumps(row) for row in rows)
    return ("\n".join(lines) + "\n").encode("utf-8")


def upload_ndjson(dataset_name: str, date_str: str, rows: list[dict[str, Any]]) -> str:
    key = f"{dataset_name}/dt={date_str}/data.ndjson"
    body = _rows_to_ndjson(rows)
    s3 = boto3.client("s3")
    last_error = ""

    for attempt, backoff in enumerate((0,) + RETRY_BACKOFF_SECONDS, start=1):
        if backoff:
            time.sleep(backoff)

        try:
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=key,
                Body=body,
                ContentType="application/x-ndjson")
            return key

        except ClientError as exc:
            last_error = str(exc)

        if attempt > MAX_RETRIES:
            break

    raise S3LoaderError(
        f"failed to upload s3://{BUCKET_NAME}/{key} after {MAX_RETRIES} retries: {last_error}")
