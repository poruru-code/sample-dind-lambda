from services.gateway.config import GatewayConfig
from services.common.core.config import BaseAppConfig


def test_gateway_config_inheritance():
    """
    TDD: GatewayConfig should inherit from BaseAppConfig.
    """
    assert issubclass(GatewayConfig, BaseAppConfig)


def test_gateway_config_fields():
    """
    TDD: GatewayConfig should have ORCHESTRATOR_URL and ORCHESTRATOR_TIMEOUT.
    """
    config = GatewayConfig()
    assert hasattr(config, "ORCHESTRATOR_URL")
    assert hasattr(config, "ORCHESTRATOR_TIMEOUT")
    # Verify default values (optional, but good for regression)
    assert config.ORCHESTRATOR_URL == "http://test-manager:8081"
    assert config.ORCHESTRATOR_TIMEOUT == 30.0
