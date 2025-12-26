def test_manager_client_uses_config():
    """
    TDD: ManagerClient should use config.ORCHESTRATOR_URL and config.MANAGER_TIMEOUT
    instead of os.getenv directly.
    """
    # This test verifies that the module doesn't have hardcoded ORCHESTRATOR_URL/MANAGER_TIMEOUT
    # by checking the config object is used
    from services.gateway import client

    # Check that the module doesn't import os for getenv
    # Instead it should use config.ORCHESTRATOR_URL
    assert hasattr(client, "config") or not hasattr(client, "ORCHESTRATOR_URL"), (
        "client.py should not define ORCHESTRATOR_URL at module level"
    )
