from .shared_mocks import mock_context
import pytest


def test_auto_shutdown(m5stickv, mocker):
    from krux.auto_shutdown import auto_shutdown, seconds_counter

    ctx = mock_context(mocker)
    auto_shutdown.add_ctx(ctx)

    # Set the timeout to a value that will cause a shutdown in 2 seconds
    auto_shutdown.time_out = 1

    # Call the seconds_counter method to simulate the timer callback
    # Check if SystemExit is raised
    with pytest.raises(SystemExit):
        # Mocking timer calls:
        # Decrement the time_out value to 0
        seconds_counter("dummy timer argument")
        # Next timer call will shutdown the device
        seconds_counter("dummy timer argument")

