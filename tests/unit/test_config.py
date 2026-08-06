import pytest
from pydantic import ValidationError

from app.config import Settings


def test_default_application_branding() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "SpatialSRE-Agent"


def test_checkpoint_database_url_is_secret_and_has_local_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.checkpoint_database_url.get_secret_value() == (
        "postgresql://oncall_agent:oncall_dev@127.0.0.1:5433/oncall_agent"
    )
    assert "oncall_dev" not in repr(settings.checkpoint_database_url)


def test_checkpoint_pool_rejects_max_size_smaller_than_min_size() -> None:
    with pytest.raises(ValidationError, match="checkpoint_pool_max_size"):
        Settings(
            _env_file=None,
            checkpoint_pool_min_size=5,
            checkpoint_pool_max_size=2,
        )
