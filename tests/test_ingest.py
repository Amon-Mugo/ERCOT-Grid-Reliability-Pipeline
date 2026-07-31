# tests/test_ingest.py
#
# Unit tests for ingestion/ingest.py. fetch_dataset and upload_ndjson are
# mocked at the ingestion.ingest module level (where they're imported into),
# not at their source modules — patching the reference ingest.py actually
# calls. No real EIA/S3 network calls happen.

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from ingestion.eia_client import EIAClientError
from ingestion.ingest import DATASET, get_yesterday_window, run_ingestion
from ingestion.s3_loader import S3LoaderError


# ---------------------------------------------------------------------
# get_yesterday_window
# ---------------------------------------------------------------------


def test_get_yesterday_window_returns_correct_format():
    date_str, start, end = get_yesterday_window()

    assert len(date_str) == 10  # YYYY-MM-DD
    assert start == f"{date_str}T00"
    assert end == f"{date_str}T23"


def test_get_yesterday_window_is_actually_yesterday_utc():
    date_str, _, _ = get_yesterday_window()
    expected = datetime.now(timezone.utc).date().isoformat()
    # date_str should be one day before "today" in UTC
    from datetime import timedelta

    yesterday_expected = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).strftime("%Y-%m-%d")
    assert date_str == yesterday_expected
    assert date_str != expected


# ---------------------------------------------------------------------
# run_ingestion
# ---------------------------------------------------------------------


@patch("ingestion.ingest.upload_ndjson")
@patch("ingestion.ingest.fetch_dataset")
def test_run_ingestion_all_datasets_succeed(mock_fetch, mock_upload):
    mock_fetch.return_value = [{"period": "2026-07-26T00", "value": 100}]
    mock_upload.return_value = "demand/dt=2026-07-26/data.ndjson"

    run_ingestion()  # should not raise

    assert mock_fetch.call_count == len(DATASET)
    assert mock_upload.call_count == len(DATASET)


@patch("ingestion.ingest.upload_ndjson")
@patch("ingestion.ingest.fetch_dataset")
def test_run_ingestion_continues_past_single_failure_then_raises(
    mock_fetch, mock_upload
):
    # demand fails at fetch, others succeed
    def fetch_side_effect(route, facets, start, end):
        if facets.get("type") == ["D"]:
            raise EIAClientError("simulated EIA failure")
        return [{"period": "2026-07-26T00", "value": 1}]

    mock_fetch.side_effect = fetch_side_effect
    mock_upload.return_value = "some/key.ndjson"

    with pytest.raises(RuntimeError, match="demand"):
        run_ingestion()

    # all datasets were still attempted, not stopped short
    assert mock_fetch.call_count == len(DATASET)
    # upload only called for the 2 datasets that didn't fail at fetch
    assert mock_upload.call_count == len(DATASET) - 1


@patch("ingestion.ingest.upload_ndjson")
@patch("ingestion.ingest.fetch_dataset")
def test_run_ingestion_s3_failure_also_collected(mock_fetch, mock_upload):
    mock_fetch.return_value = [{"period": "2026-07-26T00", "value": 1}]
    mock_upload.side_effect = S3LoaderError("simulated S3 failure")

    with pytest.raises(RuntimeError) as exc_info:
        run_ingestion()

    # all three dataset names should appear in the failure message
    for dataset_name in DATASET:
        assert dataset_name in str(exc_info.value)


@patch("ingestion.ingest.upload_ndjson")
@patch("ingestion.ingest.fetch_dataset")
def test_run_ingestion_all_fail_lists_all_in_error(mock_fetch, mock_upload):
    mock_fetch.side_effect = EIAClientError("down")

    with pytest.raises(RuntimeError) as exc_info:
        run_ingestion()

    message = str(exc_info.value)
    for dataset_name in DATASET:
        assert dataset_name in message
    assert mock_upload.call_count == 0


@patch("ingestion.ingest.upload_ndjson")
@patch("ingestion.ingest.fetch_dataset")
def test_run_ingestion_passes_correct_route_and_facets_per_dataset(
    mock_fetch, mock_upload
):
    mock_fetch.return_value = []
    mock_upload.return_value = "key.ndjson"

    run_ingestion()

    calls_by_dataset = {}
    for call in mock_fetch.call_args_list:
        route = call.kwargs["route"]
        facets = call.kwargs["facets"]
        calls_by_dataset[route] = facets

    # demand and interchange share the region-data route, differing by "type"
    demand_config = DATASET["demand"]
    interchange_config = DATASET["interchange"]
    generation_config = DATASET["generation_by_fuel"]

    assert generation_config["route"] == "electricity/rto/fuel-type-data/data"
    assert "type" not in generation_config["facets"]
    assert demand_config["facets"]["type"] == ["D"]
    assert interchange_config["facets"]["type"] == ["TI"]


@patch("ingestion.ingest.upload_ndjson")
@patch("ingestion.ingest.fetch_dataset")
def test_run_ingestion_uploads_with_correct_dataset_name_and_date(
    mock_fetch, mock_upload
):
    mock_fetch.return_value = [{"value": 1}]
    mock_upload.return_value = "key.ndjson"

    run_ingestion()

    uploaded_dataset_names = {
        call.args[0] for call in mock_upload.call_args_list
    }
    assert uploaded_dataset_names == set(DATASET.keys())