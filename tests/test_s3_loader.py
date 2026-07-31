# tests/test_s3_loader.py
#
# Unit tests for ingestion/s3_loader.py. No real AWS calls — boto3.client("s3")
# is patched at the point s3_loader imports boto3, so put_object is a MagicMock
# throughout. time.sleep is patched so retry tests run instantly.

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from ingestion.s3_loader import (
    BUCKET_NAME,
    MAX_RETRIES,
    S3LoaderError,
    _rows_to_ndjson,
    upload_ndjson,
)


def _client_error(code="InternalError", message="something broke"):
    return ClientError(
        error_response={"Error": {"Code": code, "Message": message}},
        operation_name="PutObject",
    )


# ---------------------------------------------------------------------
# _rows_to_ndjson
# ---------------------------------------------------------------------


def test_rows_to_ndjson_formats_one_row_per_line():
    rows = [{"a": 1}, {"b": 2}]
    result = _rows_to_ndjson(rows)

    assert isinstance(result, bytes)
    lines = result.decode("utf-8").splitlines()
    assert lines == [json.dumps({"a": 1}), json.dumps({"b": 2})]


def test_rows_to_ndjson_ends_with_trailing_newline():
    result = _rows_to_ndjson([{"a": 1}])
    assert result.endswith(b"\n")


def test_rows_to_ndjson_empty_list_returns_just_newline():
    result = _rows_to_ndjson([])
    assert result == b"\n"


# ---------------------------------------------------------------------
# upload_ndjson
# ---------------------------------------------------------------------


@patch("ingestion.s3_loader.time.sleep")
@patch("ingestion.s3_loader.boto3.client")
def test_upload_ndjson_success_first_attempt(mock_boto_client, mock_sleep):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    key = upload_ndjson("demand", "2026-07-26", [{"value": 100}])

    assert key == "demand/dt=2026-07-26/data.ndjson"
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == BUCKET_NAME
    assert call_kwargs["Key"] == "demand/dt=2026-07-26/data.ndjson"
    assert call_kwargs["ContentType"] == "application/x-ndjson"
    assert call_kwargs["Body"] == _rows_to_ndjson([{"value": 100}])
    mock_sleep.assert_not_called()


@patch("ingestion.s3_loader.time.sleep")
@patch("ingestion.s3_loader.boto3.client")
def test_upload_ndjson_retries_then_succeeds(mock_boto_client, mock_sleep):
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = [_client_error(), None]
    mock_boto_client.return_value = mock_s3

    key = upload_ndjson("interchange", "2026-07-26", [{"value": 1}])

    assert key == "interchange/dt=2026-07-26/data.ndjson"
    assert mock_s3.put_object.call_count == 2
    mock_sleep.assert_called_once_with(20)


@patch("ingestion.s3_loader.time.sleep")
@patch("ingestion.s3_loader.boto3.client")
def test_upload_ndjson_raises_after_max_retries(mock_boto_client, mock_sleep):
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = _client_error(
        code="AccessDenied", message="not authorized"
    )
    mock_boto_client.return_value = mock_s3

    with pytest.raises(S3LoaderError, match=f"after {MAX_RETRIES} retries"):
        upload_ndjson("generation_by_fuel", "2026-07-26", [{"value": 1}])

    assert mock_s3.put_object.call_count == MAX_RETRIES + 1
    assert mock_sleep.call_count == 3
    mock_sleep.assert_any_call(20)
    mock_sleep.assert_any_call(30)
    mock_sleep.assert_any_call(40)


@patch("ingestion.s3_loader.time.sleep")
@patch("ingestion.s3_loader.boto3.client")
def test_upload_ndjson_error_message_includes_key(mock_boto_client, mock_sleep):
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = _client_error()
    mock_boto_client.return_value = mock_s3

    with pytest.raises(S3LoaderError, match=r"demand/dt=2026-07-26/data\.ndjson"):
        upload_ndjson("demand", "2026-07-26", [{"value": 1}])


@patch("ingestion.s3_loader.time.sleep")
@patch("ingestion.s3_loader.boto3.client")
def test_upload_ndjson_builds_correct_key_per_dataset_and_date(
    mock_boto_client, mock_sleep
):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    key = upload_ndjson("fuel_mix", "2026-01-05", [])

    assert key == "fuel_mix/dt=2026-01-05/data.ndjson"