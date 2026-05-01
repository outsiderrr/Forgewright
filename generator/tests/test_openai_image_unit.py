"""OpenAIImageProvider unit tests — fully mocked SDK, no network.

Covers:
  - generate() decodes b64_json into bytes and returns mode="api"
  - target_ref / target_type / asset_role / variant_label round-trip into
    raw_metadata (Protocol contract; matches ManualImportProvider)
  - openai_response is captured into raw_metadata for trace
  - estimate_cost is the conservative high-tier upper bound
  - missing OPENAI_API_KEY at construction raises ImageProviderError
  - OpenAI SDK errors are wrapped as ImageProviderError (no leak)
  - response with no data / no b64_json fails as ImageProviderError
  - ref_images fallback: paths get appended to the prompt text (no upload)
  - size tuple is converted to "WIDTHxHEIGHT" string
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from openai import OpenAIError

from generator.image_provider import ImageGenerationResult, ImageProvider, ImageProviderError
from generator.providers import OpenAIImageProvider


# A 1×1 transparent PNG, base64 encoded. Used as the SDK's b64_json payload
# in mocks so we exercise real base64 decoding rather than trusting the mock.
_TINY_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63000100000005000100"
    "0d0a2db40000000049454e44ae426082"
)
_TINY_PNG_B64 = base64.b64encode(_TINY_PNG_BYTES).decode("ascii")


def _make_mock_response(b64: str = _TINY_PNG_B64) -> MagicMock:
    """Stand-in for openai.types.ImagesResponse with .data[0].b64_json set."""
    image = MagicMock()
    image.b64_json = b64
    image.url = None
    response = MagicMock()
    response.data = [image]
    response.model_dump.return_value = {
        "created": 1700000000,
        "data": [{"b64_json": b64, "url": None}],
        "size": "1024x1024",
    }
    return response


def _make_provider_with_mock_client(monkeypatch) -> tuple[OpenAIImageProvider, MagicMock]:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    provider = OpenAIImageProvider()
    mock_client = MagicMock()
    # Override the cached client so the lazy property returns our mock.
    provider._client_cache = mock_client  # type: ignore[attr-defined]
    return provider, mock_client


def test_constructor_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ImageProviderError):
        OpenAIImageProvider()


def test_constructor_accepts_explicit_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIImageProvider(api_key="sk-explicit")
    assert provider.model_id == "gpt-image-1"


def test_provider_satisfies_protocol(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    provider = OpenAIImageProvider()
    assert isinstance(provider, ImageProvider)


def test_generate_returns_api_result_with_decoded_bytes(monkeypatch) -> None:
    provider, mock_client = _make_provider_with_mock_client(monkeypatch)
    mock_client.images.generate.return_value = _make_mock_response()

    result = provider.generate(
        prompt="A character sheet of Vellin, painterly style.",
        asset_kind="character_sheet",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_vellin_neutral",
        variant_label="neutral",
    )

    assert isinstance(result, ImageGenerationResult)
    assert result.mode == "api"
    assert result.asset_id_stub == "img_vellin_neutral"
    assert result.image_bytes == _TINY_PNG_BYTES
    assert result.prompt_package_path is None
    assert result.cost_usd == pytest.approx(0.17)
    assert result.raw_metadata["target_ref"] == "char_vellin"
    assert result.raw_metadata["target_type"] == "character"
    assert result.raw_metadata["asset_role"] == "character_sheet"
    assert result.raw_metadata["variant_label"] == "neutral"
    assert result.raw_metadata["model_id"] == "gpt-image-1"
    assert result.raw_metadata["size_requested"] == [1024, 1024]
    assert "openai_response" in result.raw_metadata


def test_generate_passes_size_as_openai_string(monkeypatch) -> None:
    provider, mock_client = _make_provider_with_mock_client(monkeypatch)
    mock_client.images.generate.return_value = _make_mock_response()

    provider.generate(
        prompt="x",
        size=(1024, 1536),
        asset_kind="character_sheet",
        target_ref="char_x",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_x_neutral",
    )

    call_kwargs = mock_client.images.generate.call_args.kwargs
    assert call_kwargs["model"] == "gpt-image-1"
    assert call_kwargs["size"] == "1024x1536"
    assert call_kwargs["n"] == 1


def test_generate_appends_ref_image_paths_to_prompt(monkeypatch) -> None:
    provider, mock_client = _make_provider_with_mock_client(monkeypatch)
    mock_client.images.generate.return_value = _make_mock_response()

    ref_paths = [Path("content/visuals/_reference/vellin.png")]
    provider.generate(
        prompt="base prompt",
        ref_images=ref_paths,
        asset_kind="character_sheet",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_vellin_neutral",
    )

    sent_prompt = mock_client.images.generate.call_args.kwargs["prompt"]
    assert "base prompt" in sent_prompt
    assert "Reference images" in sent_prompt
    assert str(ref_paths[0]) in sent_prompt


def test_generate_omits_reference_block_when_no_refs(monkeypatch) -> None:
    provider, mock_client = _make_provider_with_mock_client(monkeypatch)
    mock_client.images.generate.return_value = _make_mock_response()

    provider.generate(
        prompt="exact prompt",
        ref_images=None,
        asset_kind="character_sheet",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_id_stub="img_vellin_neutral",
    )

    sent_prompt = mock_client.images.generate.call_args.kwargs["prompt"]
    assert sent_prompt == "exact prompt"


def test_generate_wraps_openai_error_as_provider_error(monkeypatch) -> None:
    provider, mock_client = _make_provider_with_mock_client(monkeypatch)
    mock_client.images.generate.side_effect = OpenAIError("boom")

    with pytest.raises(ImageProviderError) as ei:
        provider.generate(
            prompt="x",
            asset_kind="character_sheet",
            target_ref="char_x",
            target_type="character",
            asset_role="character_sheet",
            asset_id_stub="img_x_neutral",
        )
    # Original exception is chained for debugging.
    assert isinstance(ei.value.__cause__, OpenAIError)


def test_generate_raises_when_response_has_no_data(monkeypatch) -> None:
    provider, mock_client = _make_provider_with_mock_client(monkeypatch)
    empty = MagicMock()
    empty.data = []
    empty.model_dump.return_value = {"data": []}
    mock_client.images.generate.return_value = empty

    with pytest.raises(ImageProviderError, match="no `data` field"):
        provider.generate(
            prompt="x",
            asset_kind="character_sheet",
            target_ref="char_x",
            target_type="character",
            asset_role="character_sheet",
            asset_id_stub="img_x_neutral",
        )


def test_generate_raises_when_response_has_no_b64_or_url(monkeypatch) -> None:
    provider, mock_client = _make_provider_with_mock_client(monkeypatch)
    bad_image = MagicMock()
    bad_image.b64_json = None
    bad_image.url = None
    bad_response = MagicMock()
    bad_response.data = [bad_image]
    bad_response.model_dump.return_value = {"data": [{}]}
    mock_client.images.generate.return_value = bad_response

    with pytest.raises(ImageProviderError, match="b64_json"):
        provider.generate(
            prompt="x",
            asset_kind="character_sheet",
            target_ref="char_x",
            target_type="character",
            asset_role="character_sheet",
            asset_id_stub="img_x_neutral",
        )


def test_generate_raises_on_malformed_base64(monkeypatch) -> None:
    provider, mock_client = _make_provider_with_mock_client(monkeypatch)
    image = MagicMock()
    image.b64_json = "not valid base64 !@#$"
    image.url = None
    response = MagicMock()
    response.data = [image]
    response.model_dump.return_value = {"data": [{}]}
    mock_client.images.generate.return_value = response

    with pytest.raises(ImageProviderError, match="malformed base64"):
        provider.generate(
            prompt="x",
            asset_kind="character_sheet",
            target_ref="char_x",
            target_type="character",
            asset_role="character_sheet",
            asset_id_stub="img_x_neutral",
        )


def test_estimate_cost_uses_conservative_upper_bound(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    provider = OpenAIImageProvider()
    # 1 image at high tier ≈ $0.17 per OpenAI pricing 2026-05-01
    assert provider.estimate_cost(n=1, size=(1024, 1024)) == pytest.approx(0.17)
    # Linear scaling in n
    assert provider.estimate_cost(n=4, size=(1024, 1024)) == pytest.approx(0.68)
    # Cost is size-independent at this stage (deliberate; T-1.5.9 §2)
    assert provider.estimate_cost(n=1, size=(1536, 1024)) == pytest.approx(0.17)
