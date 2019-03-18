"""
Unit tests for the enrollment.tasks module.
"""
import mock

from registrar.apps.enrollments import tasks


@mock.patch('registrar.apps.enrollments.tasks.log', autospec=True)
def test_debug_task_happy_path(mock_logger):
    tasks.debug_task.apply_async([1, 2], kwargs={'foo': 'bar'})

    assert 1 == mock_logger.debug.call_count
    debug_call_argument = mock_logger.debug.call_args_list[0][0][0]
    assert "'args': [1, 2]" in debug_call_argument
    assert "'kwargs': {'foo': 'bar'}" in debug_call_argument
