from umami_worker.main import tick

def test_worker_is_inert_until_execution_implemented():
    assert tick() == "idle"
