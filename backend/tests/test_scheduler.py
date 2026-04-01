"""Tests for scheduler and tasks module imports."""

from app.workers.scheduler import start_scheduler, stop_scheduler, scheduler
from app.workers.tasks import _get_available_engines


class TestSchedulerConfig:
    def test_scheduler_importable(self):
        assert scheduler is not None

    def test_start_stop_functions_exist(self):
        assert callable(start_scheduler)
        assert callable(stop_scheduler)


class TestTasksConfig:
    def test_get_available_engines_returns_list(self):
        engines = _get_available_engines()
        assert isinstance(engines, list)

    def test_task_functions_importable(self):
        from app.workers.tasks import run_capture_for_brand, compute_daily_scores, run_daily_capture_all
        assert callable(run_capture_for_brand)
        assert callable(compute_daily_scores)
        assert callable(run_daily_capture_all)
