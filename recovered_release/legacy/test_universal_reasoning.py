import pytest
import asyncio
from unittest.mock import MagicMock

from universal_reasoning import UniversalReasoning, load_json_config, CustomRecognizer, RecognizerResult

# Mocked config
MOCK_CONFIG = {
    "enabled_perspectives": [],
    "ethical_considerations": "Respect all sentient patterns."
}

@pytest.fixture
def reasoning_engine():
    engine = UniversalReasoning(MOCK_CONFIG)
    engine.perspectives = []  # Skip real perspectives
    engine.memory_handler.save = MagicMock()
    engine.reweaver.record_dream = MagicMock()
    engine.cocooner.wrap_and_store = MagicMock()
    return engine

@pytest.mark.asyncio
async def test_generate_response_basic(reasoning_engine):
    response = await reasoning_engine.generate_response("What is hydrogen?")
    assert "Ethical Considerations" in response
    assert any(el.name in response for el in reasoning_engine.elements)

@pytest.mark.asyncio
async def test_generate_response_no_trigger(reasoning_engine):
    response = await reasoning_engine.generate_response("Tell me a joke about stars.")
    assert "Ethical Considerations" in response


def test_load_json_config_valid(tmp_path):
    config_file = tmp_path / "test_config.json"
    config_file.write_text('{"enabled_perspectives": ["newton"]}')
    config = load_json_config(str(config_file))
    assert config["enabled_perspectives"] == ["newton"]


def test_load_json_config_invalid(tmp_path):
    bad_file = tmp_path / "bad_config.json"
    bad_file.write_text('{ bad json')
    config = load_json_config(str(bad_file))
    assert config == {}


def test_custom_recognizer_match():
    recognizer = CustomRecognizer()
    result = recognizer.recognize("Does hydrogen have defense?")
    assert isinstance(result, RecognizerResult)
    assert result.text


def test_custom_recognizer_no_match():
    recognizer = CustomRecognizer()
    result = recognizer.recognize("What is love?")
    assert result.text is None

