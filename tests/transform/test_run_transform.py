# tests/transform/test_run_transform.py
#
# Verifies the EMR Serverless entry point's control flow: per-dataset
# isolation (one dataset's failure doesn't block the others), no curated
# write on validation failure, and a non-zero exit if anything failed.
# Everything here is mocked — no real Spark session, no real S3 I/O —
# since this file tests orchestration logic, not data transforms.

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, call

import pytest

from src.transform import run_transform
from src.transform.validators import TransformValidationError


class TestComputeIngestionDate:
    def test_returns_a_date_object(self):
        result = run_transform.compute_ingestion_date()
        assert isinstance(result, date)

    def test_returns_yesterday_in_utc(self):
        result = run_transform.compute_ingestion_date()
        today_utc = datetime.now(timezone.utc).date()
        # Allow for the (rare) case this test runs exactly at UTC midnight.
        assert (today_utc - result).days in (1, 2)


class TestPathBuilders:
    def test_raw_path_format(self):
        path = run_transform.raw_path("demand", date(2026, 8, 8))
        assert path == "s3://ercot-grid-pipeline-raw/demand/dt=2026-08-08/data.ndjson"

    def test_curated_path_format(self):
        path = run_transform.curated_path("demand", date(2026, 8, 8))
        assert path == "s3://ercot-grid-pipeline-curated/demand/dt=2026-08-08/"


class TestRunIsolation:
    """Tests the run() function's per-dataset try/except behavior by
    replacing module-level read_raw, write_curated, and DATASETS with
    controllable mocks."""

    def _patch_datasets(self, monkeypatch, dataset_behaviors: dict):
        """dataset_behaviors maps dataset name -> a transform_fn mock
        (side_effect set by the caller). Schema is irrelevant since
        read_raw is also mocked."""
        fake_datasets = {
            name: (MagicMock(name=f"{name}_schema"), transform_fn)
            for name, transform_fn in dataset_behaviors.items()
        }
        monkeypatch.setattr(run_transform, "DATASETS", fake_datasets)

    def test_all_datasets_succeed_returns_empty_failure_list(self, monkeypatch):
        transform_demand = MagicMock(return_value="curated_demand_df")
        transform_interchange = MagicMock(return_value="curated_interchange_df")
        transform_generation = MagicMock(return_value="curated_generation_df")

        self._patch_datasets(
            monkeypatch,
            {
                "demand": transform_demand,
                "interchange": transform_interchange,
                "generation_by_fuel": transform_generation,
            },
        )
        monkeypatch.setattr(run_transform, "read_raw", MagicMock(return_value="raw_df"))
        write_curated_mock = MagicMock()
        monkeypatch.setattr(run_transform, "write_curated", write_curated_mock)

        failed = run_transform.run(MagicMock(), date(2026, 8, 8))

        assert failed == []
        assert write_curated_mock.call_count == 3

    def test_one_dataset_validation_failure_does_not_block_others(self, monkeypatch):
        transform_demand = MagicMock(return_value="curated_demand_df")
        transform_interchange = MagicMock(
            side_effect=TransformValidationError("bad interchange data")
        )
        transform_generation = MagicMock(return_value="curated_generation_df")

        self._patch_datasets(
            monkeypatch,
            {
                "demand": transform_demand,
                "interchange": transform_interchange,
                "generation_by_fuel": transform_generation,
            },
        )
        monkeypatch.setattr(run_transform, "read_raw", MagicMock(return_value="raw_df"))
        write_curated_mock = MagicMock()
        monkeypatch.setattr(run_transform, "write_curated", write_curated_mock)

        failed = run_transform.run(MagicMock(), date(2026, 8, 8))

        assert failed == ["interchange"]
        # demand and generation still ran and still got written.
        transform_demand.assert_called_once()
        transform_generation.assert_called_once()
        assert write_curated_mock.call_count == 2

    def test_failed_dataset_is_never_written_to_curated(self, monkeypatch):
        transform_demand = MagicMock(
            side_effect=TransformValidationError("bad demand data")
        )

        self._patch_datasets(monkeypatch, {"demand": transform_demand})
        monkeypatch.setattr(run_transform, "read_raw", MagicMock(return_value="raw_df"))
        write_curated_mock = MagicMock()
        monkeypatch.setattr(run_transform, "write_curated", write_curated_mock)

        run_transform.run(MagicMock(), date(2026, 8, 8))

        write_curated_mock.assert_not_called()

    def test_all_datasets_fail_returns_all_in_failure_list(self, monkeypatch):
        transform_demand = MagicMock(side_effect=TransformValidationError("bad"))
        transform_interchange = MagicMock(side_effect=TransformValidationError("bad"))
        transform_generation = MagicMock(side_effect=TransformValidationError("bad"))

        self._patch_datasets(
            monkeypatch,
            {
                "demand": transform_demand,
                "interchange": transform_interchange,
                "generation_by_fuel": transform_generation,
            },
        )
        monkeypatch.setattr(run_transform, "read_raw", MagicMock(return_value="raw_df"))
        write_curated_mock = MagicMock()
        monkeypatch.setattr(run_transform, "write_curated", write_curated_mock)

        failed = run_transform.run(MagicMock(), date(2026, 8, 8))

        assert sorted(failed) == ["demand", "generation_by_fuel", "interchange"]
        write_curated_mock.assert_not_called()

    def test_unexpected_non_validation_exception_is_also_isolated(self, monkeypatch):
        # run() catches Exception broadly, not just TransformValidationError,
        # so an unrelated bug in one dataset shouldn't take down the others.
        transform_demand = MagicMock(side_effect=RuntimeError("s3 read timed out"))
        transform_interchange = MagicMock(return_value="curated_interchange_df")

        self._patch_datasets(
            monkeypatch,
            {"demand": transform_demand, "interchange": transform_interchange},
        )
        monkeypatch.setattr(run_transform, "read_raw", MagicMock(return_value="raw_df"))
        write_curated_mock = MagicMock()
        monkeypatch.setattr(run_transform, "write_curated", write_curated_mock)

        failed = run_transform.run(MagicMock(), date(2026, 8, 8))

        assert failed == ["demand"]
        assert write_curated_mock.call_count == 1


class TestMainExitBehavior:
    def test_exits_zero_implicitly_when_all_datasets_succeed(self, monkeypatch):
        monkeypatch.setattr(run_transform, "get_spark_session", MagicMock())
        monkeypatch.setattr(
            run_transform, "compute_ingestion_date", MagicMock(return_value=date(2026, 8, 8))
        )
        monkeypatch.setattr(run_transform, "run", MagicMock(return_value=[]))
        exit_mock = MagicMock()
        monkeypatch.setattr(run_transform.sys, "exit", exit_mock)

        run_transform.main()

        exit_mock.assert_not_called()

    def test_exits_one_when_any_dataset_failed(self, monkeypatch):
        monkeypatch.setattr(run_transform, "get_spark_session", MagicMock())
        monkeypatch.setattr(
            run_transform, "compute_ingestion_date", MagicMock(return_value=date(2026, 8, 8))
        )
        monkeypatch.setattr(run_transform, "run", MagicMock(return_value=["interchange"]))
        exit_mock = MagicMock()
        monkeypatch.setattr(run_transform.sys, "exit", exit_mock)

        run_transform.main()

        exit_mock.assert_called_once_with(1)

    def test_spark_session_is_stopped_even_when_datasets_failed(self, monkeypatch):
        spark_mock = MagicMock()
        monkeypatch.setattr(
            run_transform, "get_spark_session", MagicMock(return_value=spark_mock)
        )
        monkeypatch.setattr(
            run_transform, "compute_ingestion_date", MagicMock(return_value=date(2026, 8, 8))
        )
        monkeypatch.setattr(run_transform, "run", MagicMock(return_value=["demand"]))
        monkeypatch.setattr(run_transform.sys, "exit", MagicMock())

        run_transform.main()

        spark_mock.stop.assert_called_once()

    def test_spark_session_is_stopped_even_when_run_raises(self, monkeypatch):
        # spark.stop() lives in a finally block — confirm it still fires if
        # run() itself blows up unexpectedly (not just a per-dataset failure).
        spark_mock = MagicMock()
        monkeypatch.setattr(
            run_transform, "get_spark_session", MagicMock(return_value=spark_mock)
        )
        monkeypatch.setattr(
            run_transform, "compute_ingestion_date", MagicMock(return_value=date(2026, 8, 8))
        )
        monkeypatch.setattr(
            run_transform, "run", MagicMock(side_effect=RuntimeError("unexpected"))
        )

        with pytest.raises(RuntimeError):
            run_transform.main()

        spark_mock.stop.assert_called_once()