import json
import asyncio
import types
import pytest

from llm_manager import LLMManager


class FakeBoto3Client:
    def __init__(self):
        self.calls = []
        self.last_payload = None

    class _Body:
        def __init__(self, data_dict):
            self._data = json.dumps(data_dict).encode("utf-8")

        def read(self):
            return self._data

    def invoke_model(self, *, modelId, body, contentType, accept):
        self.last_payload = json.loads(body)
        self.calls.append({
            "modelId": modelId,
            "contentType": contentType,
            "accept": accept,
        })
        # Return a response that matches provider expectations
        return {
            "body": self._Body({"fake": "sync_response", "echo": self.last_payload})
        }


class FakeAioBody:
    def __init__(self, data_dict):
        self._data = json.dumps(data_dict).encode("utf-8")

    async def read(self):
        return self._data


class FakeAioBoto3Client:
    def __init__(self):
        self.calls = []
        self.last_payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def invoke_model(self, *, modelId, body, contentType, accept):
        self.last_payload = json.loads(body)
        self.calls.append({
            "modelId": modelId,
            "contentType": contentType,
            "accept": accept,
        })
        return {
            "body": FakeAioBody({"fake": "async_response", "echo": self.last_payload})
        }


class FakeAioSession:
    def __init__(self, client_instance: FakeAioBoto3Client):
        self._client_instance = client_instance

    def client(self, *, service_name, region_name, aws_access_key_id, aws_secret_access_key):
        return self._client_instance


@pytest.fixture()
def test_config():
    return {
        "default_provider": "bedrock",
        "default_model": "bedrock/claude-sonnet-3.7",
        "providers": {
            "bedrock": {
                "enabled": True,
                "region_name": "us-east-2",
                "aws_access_key_id": "test",
                "aws_secret_access_key": "test",
                "models": {
                    "claude-sonnet-3.7": {
                        "model_id": "arn:aws:bedrock:us-east-2:123:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                        "thinking_supported": True,
                    }
                }
            }
        }
    }


def test_bedrock_generate_sync(monkeypatch, test_config):
    fake_client = FakeBoto3Client()

    # Monkeypatch boto3.client factory to return our fake client
    import llm_manager.providers.bedrock as bedrock_mod

    def fake_boto3_client(*, service_name, region_name, aws_access_key_id, aws_secret_access_key):
        assert service_name == "bedrock-runtime"
        return fake_client

    monkeypatch.setattr(bedrock_mod, "boto3", types.SimpleNamespace(client=fake_boto3_client))

    # Monkeypatch config loader to return our test config
    import llm_manager.utils.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "load_config", lambda path=None: test_config)

    manager = LLMManager()
    result = manager.generate(
        "Hello",
        model="bedrock/claude-sonnet-3.7",
        max_tokens=256,
        thinking_tokens=128,
        temperature=0.2,
        system="You are a helpful assistant.",
    )

    # Response round-tripped
    assert result["fake"] == "sync_response"
    # Ensure thinking is passed through for supported model
    assert fake_client.last_payload["thinking"] == {"type": "enabled", "budget_tokens": 128}
    # Ensure basic fields present
    assert fake_client.last_payload["messages"][0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_bedrock_generate_async(monkeypatch, test_config):
    fake_async_client = FakeAioBoto3Client()
    fake_session = FakeAioSession(fake_async_client)

    import llm_manager.providers.bedrock as bedrock_mod

    # Patch aioboto3.Session to our fake
    monkeypatch.setattr(bedrock_mod, "aioboto3", types.SimpleNamespace(Session=lambda: fake_session))

    # Monkeypatch config loader to return our test config
    import llm_manager.utils.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "load_config", lambda path=None: test_config)

    manager = LLMManager()
    result = await manager.generate_async(
        "Hi",
        model="bedrock/claude-sonnet-3.7",
        max_tokens=64,
        thinking_tokens=42,
        temperature=0.5,
        system="You are concise.",
    )

    # Response round-tripped
    assert result["fake"] == "async_response"
    # Ensure thinking is passed through for supported model
    assert fake_async_client.last_payload["thinking"] == {"type": "enabled", "budget_tokens": 42}
    # Ensure basic fields present
    assert fake_async_client.last_payload["messages"][0]["content"] == "Hi"


def test_bedrock_user_payload_sync(monkeypatch, test_config):
    fake_client = FakeBoto3Client()

    import llm_manager.providers.bedrock as bedrock_mod

    def fake_boto3_client(*, service_name, region_name, aws_access_key_id, aws_secret_access_key):
        return fake_client

    monkeypatch.setattr(bedrock_mod, "boto3", types.SimpleNamespace(client=fake_boto3_client))

    import llm_manager.utils.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "load_config", lambda path=None: test_config)

    manager = LLMManager()
    # Provide a raw payload and ensure it's sent verbatim
    raw_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "system": "S",
        "messages": [{"role": "user", "content": "Custom"}],
        "temperature": 0.33,
    }
    result = manager.generate(
        "ignored",  # should be ignored when payload is provided
        model="bedrock/claude-sonnet-3.7",
        payload=raw_payload,
    )

    assert result["fake"] == "sync_response"
    assert fake_client.last_payload == raw_payload


@pytest.mark.asyncio
async def test_bedrock_user_payload_async(monkeypatch, test_config):
    fake_async_client = FakeAioBoto3Client()
    fake_session = FakeAioSession(fake_async_client)

    import llm_manager.providers.bedrock as bedrock_mod
    monkeypatch.setattr(bedrock_mod, "aioboto3", types.SimpleNamespace(Session=lambda: fake_session))

    import llm_manager.utils.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "load_config", lambda path=None: test_config)

    manager = LLMManager()
    # Provide a raw payload and ensure it's sent verbatim
    raw_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "system": "S2",
        "messages": [{"role": "user", "content": "Custom-Async"}],
        "temperature": 0.11,
    }
    result = await manager.generate_async(
        "ignored",
        model="bedrock/claude-sonnet-3.7",
        payload=raw_payload,
    )

    assert result["fake"] == "async_response"
    assert fake_async_client.last_payload == raw_payload


