#  this is a thin wrapper around the EIA API

import os
import time
from typing import Any  # enable values of any datatype
import requests

BASE_URL = "https://api.eia.gov/v2"
PAGE_LENGTH = 5000
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (20, 30, 40)
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}  # rate limiting


class EIAClientError(Exception):
    pass  # class to handle errors but intentionally empty


def _get_api_key() -> str:
    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        raise EIAClientError("EIA_API_KEY environment variable not set")
    return api_key


# internal helper function
def _request_page(
        session: requests.Session, router: str, params: list[tuple[str, str]]) -> dict[str, Any]:

    clean_route = router.lstrip("/")
    url = f"{BASE_URL}/{clean_route}"
    last_error = ""

    for attempt, backoff in enumerate((0,) + RETRY_BACKOFF_SECONDS, start=1):
        if backoff:
            time.sleep(backoff)

        try:
            response = session.get(url, params=params, timeout=30)

            if response.status_code == 200:  # success
                return response.json()  # success

            last_error = f"HTTP {response.status_code} :{response.text[:200]}"

            if response.status_code not in RETRY_STATUS_CODES:
                raise EIAClientError(
                    f"request failed with status code {last_error}"
                )

        except requests.exceptions.RequestException as exc:
            last_error = f"Netwok/Connection error: {exc}"

        if attempt > MAX_RETRIES:
            break

    raise EIAClientError(
        f"EIA API request failed after {MAX_RETRIES} attempts: {last_error}"
    )


# main function  it is responsible for fetching the data
# helps us to fetch which data and use only TEXAS data
def fetch_dataset(
    route: str,  # e.g. /series/d/electricity/production/total/us
    facets: dict[
        str, list[str]
    ],  # e.g. {"respondent": ["ERCO"], "type": ["D"]}
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    api_key = _get_api_key()  # get the API key
    base_params: list[tuple[str, str]] = [
        ("frequency", "hourly"),
        ("data[0]", "value"),  # only return value
        ("start", start),  # start date
        ("end", end),  # end date
        ("sort[0][column]", "period"),  # sort by period
        ("sort[0][direction]", "asc"),  # sort in ascending order
        ("api_key", api_key),  # include the API key
    ]
    # to append the facets to the request  ad the base params and state
    for facet_name, facet_values in facets.items():  # add the facets
        for (
            value
        ) in facet_values:  # add each facet value  to use only electricity
            base_params.append((f"facets[{facet_name}][]", value))

    all_rows: list[dict[str, Any]] = []
    offset = 0

    # Share TCP connections across all paginated requests
    with requests.Session() as session:
        while True:
            page_params = base_params + [
                ("offset", str(offset)),
                ("length", str(PAGE_LENGTH)),
            ]

            payload = _request_page(session, route, page_params)
            rows = payload.get("response", {}).get("data", [])
            all_rows.extend(rows)

            if len(rows) < PAGE_LENGTH:
                break

            offset += PAGE_LENGTH

    return all_rows
