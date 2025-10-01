"""Tests for the application settings helper."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config.settings import get_settings


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Ensure environment variables are cleared between tests."""
    monkeypatch.delenv("UPLOAD_DIR", raising=False)
    monkeypatch.delenv("WEBSITE_INSTANCE_ID", raising=False)
    monkeypatch.delenv("APP_DATA_DIR", raising=False)
    yield


def test_get_settings_uses_upload_dir_overrides(monkeypatch):
    """When UPLOAD_DIR is defined it must take precedence over Azure defaults."""
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/custom-data")
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "azure-instance")

    settings = get_settings()

    assert settings.data_dir == Path("/tmp/custom-data")


def test_get_settings_defaults_to_azure_persistent_storage(monkeypatch):
    """Azure environments should persist data under /home/site/data by default."""
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "azure-instance")

    settings = get_settings()

    assert settings.data_dir == Path("/home/site/data")


def test_get_settings_allows_custom_azure_storage_path(monkeypatch):
    """A custom APP_DATA_DIR environment variable should override the Azure path."""
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "azure-instance")
    monkeypatch.setenv("APP_DATA_DIR", "/home/site/custom-path")

    settings = get_settings()

    assert settings.data_dir == Path("/home/site/custom-path")
