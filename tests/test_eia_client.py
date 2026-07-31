# tests/test_eia_client.py
#
# Unit tests for ingestion/eia_client.py. All network calls are mocked —
# session.get is a MagicMock (no real requests.Session is created for
# _request_page tests), and _request_page itself is mocked when testing
# fetch_dataset so pagination/param logic is isolated from retry logic.

from unittest.mock import MagicMock, patch

import pytest
import requests

from ingestion.eia_client import (
    BASE_URL,
    MAX_RETRIES,
    PAGE_LENGTH,
    EIAClientError,
    _get_api_key,
    _request_page,
    fetch_dataset,
)


def _make_response(status_code, json_data=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    return response


# ---------------------------------------------------------------------
# _get_api_key
# ---------------------------------------------------------------------


def test_get_api_key_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("EIA_API_KEY", "test-key-123")
    assert _get_api_key() == "test-key-123"


def test_get_api_key_raises_when_missing(monkeypatch):
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    with pytest.raises(EIAClientError, match="EIA_API_KEY"):
        _get_api_key()


# ---------------------------------------------------------------------
# _request_page
# ---------------------------------------------------------------------


@patch("ingestion.eia_client.time.sleep")
def test_request_page_success_first_attempt(mock_sleep):
    session = MagicMock()
    session.get.return_value = _make_response(
        200, {"response": {"data": [{"period": "2026-07-26T00"}]}}
    )

    result = _request_page(session, "some/route", [("a", "b")])

    assert result == {"response": {"data": [{"period": "2026-07-26T00"}]}}
    assert session.get.call_count == 1
    mock_sleep.assert_not_called()


@patch("ingestion.eia_client.time.sleep")
def test_request_page_strips_leading_slash_from_route(mock_sleep):
    session = MagicMock()
    session.get.return_value = _make_response(200, {"response": {"data": []}})

    _request_page(session, "/electricity/rto/region-data/data", [("a", "b")])

    called_url = session.get.call_args[0][0]
    assert called_url == f"{BASE_URL}/electricity/rto/region-data/data"


@patch("ingestion.eia_client.time.sleep")
def test_request_page_retries_then_succeeds(mock_sleep):
    session = MagicMock()
    session.get.side_effect = [
        _make_response(503, text="service unavailable"),
        _make_response(200, {"response": {"data": []}}),
    ]

    result = _request_page(session, "some/route", [])

    assert result == {"response": {"data": []}}
    assert session.get.call_count == 2
    mock_sleep.assert_called_once_with(20)


@patch("ingestion.eia_client.time.sleep")
def test_request_page_raises_after_max_retries_on_retryable_status(mock_sleep):
    session = MagicMock()
    session.get.return_value = _make_response(500, text="server error")

    with pytest.raises(EIAClientError, match=f"failed after {MAX_RETRIES} attempts"):
        _request_page(session, "some/route", [])

    assert session.get.call_count == MAX_RETRIES + 1
    assert mock_sleep.call_count == 3
    mock_sleep.assert_any_call(20)
    mock_sleep.assert_any_call(30)
    mock_sleep.assert_any_call(40)


@patch("ingestion.eia_client.time.sleep")
def test_request_page_fails_fast_on_non_retryable_status(mock_sleep):
    session = MagicMock()
    session.get.return_value = _make_response(404, text="not found")

    with pytest.raises(EIAClientError, match="404"):
        _request_page(session, "some/route", [])

    assert session.get.call_count == 1
    mock_sleep.assert_not_called()


@patch("ingestion.eia_client.time.sleep")
def test_request_page_network_error_then_succeeds(mock_sleep):
    session = MagicMock()
    session.get.side_effect = [
        requests.exceptions.Timeout("timed out"),
        _make_response(200, {"response": {"data": [{"x": 1}]}}),
    ]

    result = _request_page(session, "some/route", [])

    assert result == {"response": {"data": [{"x": 1}]}}
    assert session.get.call_count == 2


@patch("ingestion.eia_client.time.sleep")
def test_request_page_raises_after_persistent_network_error(mock_sleep):
    session = MagicMock()
    session.get.side_effect = requests.exceptions.ConnectionError("connection refused")

    with pytest.raises(EIAClientError, match=f"failed after {MAX_RETRIES} attempts"):
        _request_page(session, "some/route", [])

    assert session.get.call_count == MAX_RETRIES + 1


# ---------------------------------------------------------------------
# fetch_dataset
# ---------------------------------------------------------------------


@patch("ingestion.eia_client._get_api_key", return_value="fake-key")
@patch("ingestion.eia_client._request_page")
def test_fetch_dataset_single_page(mock_request_page, mock_api_key):
    mock_request_page.return_value = {
        "response": {
            "data": [
                {"period": "2026-07-26T00"},
                {"period": "2026-07-26T01"},
            ]
        }
    }

    rows = fetch_dataset(
        route="electricity/rto/region-data/data",
        facets={"respondent": ["ERCO"], "type": ["D"]},
        start="2026-07-26T00",
        end="2026-07-26T23",
    )

    assert len(rows) == 2
    assert mock_request_page.call_count == 1


@patch("ingestion.eia_client._get_api_key", return_value="fake-key")
@patch("ingestion.eia_client._request_page")
def test_fetch_dataset_builds_params_with_facets(mock_request_page, mock_api_key):
    mock_request_page.return_value = {"response": {"data": []}}

    fetch_dataset(
        route="electricity/rto/fuel-type-data/data",
        facets={"respondent": ["ERCO"], "fueltype": ["NG", "SUN"]},
        start="2026-07-26T00",
        end="2026-07-26T23",
    )

    args, _ = mock_request_page.call_args
    _, route_arg, params_arg = args

    assert route_arg == "electricity/rto/fuel-type-data/data"
    assert ("facets[respondent][]", "ERCO") in params_arg
    assert ("facets[fueltype][]", "NG") in params_arg
    assert ("facets[fueltype][]", "SUN") in params_arg
    assert ("start", "2026-07-26T00") in params_arg
    assert ("end", "2026-07-26T23") in params_arg
    assert ("api_key", "fake-key") in params_arg


@patch("ingestion.eia_client._get_api_key", return_value="fake-key")
@patch("ingestion.eia_client._request_page")
def test_fetch_dataset_paginates_until_short_page(mock_request_page, mock_api_key):
    full_page = [{"period": f"2026-07-{i:04d}"} for i in range(PAGE_LENGTH)]
    short_page = [{"period": "2026-07-27T00"}]

    mock_request_page.side_effect = [
        {"response": {"data": full_page}},
        {"response": {"data": short_page}},
    ]

    rows = fetch_dataset(
        route="electricity/rto/region-data/data",
        facets={"respondent": ["ERCO"], "type": ["D"]},
        start="2026-07-01T00",
        end="2026-07-27T00",
    )

    assert len(rows) == PAGE_LENGTH + 1
    assert mock_request_page.call_count == 2

    first_params = mock_request_page.call_args_list[0][0][2]
    second_params = mock_request_page.call_args_list[1][0][2]
    assert ("offset", "0") in first_params
    assert ("offset", str(PAGE_LENGTH)) in second_params


@patch(
    "ingestion.eia_client._get_api_key",
    side_effect=EIAClientError("EIA_API_KEY environment variable not set"),
)
def test_fetch_dataset_raises_when_api_key_missing(mock_api_key):
    with pytest.raises(EIAClientError, match="EIA_API_KEY"):
        fetch_dataset(route="x", facets={}, start="a", end="b")