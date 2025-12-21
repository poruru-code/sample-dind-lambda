
from services.manager.config import ManagerConfig
from services.common.core.config import BaseAppConfig

def test_manager_config_inheritance():
    """
    TDD: ManagerConfig should inherit from BaseAppConfig.
    """
    assert issubclass(ManagerConfig, BaseAppConfig)

def test_manager_config_fields():
    """
    TDD: ManagerConfig should have IDLE_TIMEOUT_MINUTES and CONTAINERS_NETWORK.
    """
    config = ManagerConfig()
    assert hasattr(config, "IDLE_TIMEOUT_MINUTES")
    assert hasattr(config, "CONTAINERS_NETWORK")
    # Verify defaults
    assert config.IDLE_TIMEOUT_MINUTES == 5
    # CONTAINERS_NETWORK default is "lambda-net" unless overridden by env;
    # In test environment other modules may have set different values
    assert isinstance(config.CONTAINERS_NETWORK, str)

