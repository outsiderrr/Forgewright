"""Tests for visual_review_cli (T-1.5.8).

Cover the contracts the CLI must honour:

  1. Walk results.jsonl × manifest, prompt A/R/S, and write a resumable
     visual_review_log.jsonl with the expected schema fields.
  2. Skip imports that aren't in the manifest yet (mechanical not run).
  3. `python -m generator.visual_review_cli --help` returns 0 (defends
     against a future module-name drift, per spec).

The viewer callback is injected so the test can run on any platform — we
never call macOS `open`.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from generator.manifest import Manifest, save_manifest
from generator.models._generated.image_asset import ImageAsset
from generator.visual_review_cli import run_visual_review


def _make_asset(
    asset_id: str,
    *,
    target_ref: str = "char_vellin",
    target_type: str = "character",
    asset_role: str = "character_sheet",
    asset_kind: str = "character_sheet",
) -> ImageAsset:
    return ImageAsset(
        schema_version="0.2.0",
        asset_id=asset_id,
        asset_kind=asset_kind,
        target_ref=target_ref,
        target_type=target_type,
        asset_role=asset_role,
        character_ref=target_ref if target_type == "character" else None,
        location_ref=target_ref if target_type != "character" else None,
        source_mode="manual",
        format="png",
        width=1024,
        height=1024,
        file_size_bytes=1024,
        has_alpha=(asset_role == "character_sheet"),
        file_path=f"content/visuals/vellin/{asset_id}.png",
        prompt_hash="a" * 64,
        created_at="2026-05-02T00:00:00+00:00",
    )


def _envelope(asset_id: str, *, success: bool = True, target_ref: str = "char_vellin") -> dict:
    return {
        "iter_id": 0,
        "batch_name": "t158_review",
        "target_ref": target_ref,
        "target_type": "character",
        "asset_role": "character_sheet",
        "mode": "manual",
        "result": {
            "success": success,
            "asset_id_stub": asset_id,
            "prompt_package_path": "content/visuals/_pending/" + asset_id,
            "image_bytes_size": 0,
            "failure_reason": None if success else "provider_error",
            "cost_usd": 0.0,
            "raw_metadata": {"variant_label": "neutral_torso_up"},
        },
        "generated_at": "2026-05-02T00:00:00+00:00",
    }


@pytest.fixture
def review_setup(tmp_path: Path) -> dict[str, Path]:
    """Build a synthetic batch dir + manifest with two imported assets and
    one not-yet-imported asset."""
    batch_dir = tmp_path / "20260502T120000Z_t158_review"
    batch_dir.mkdir(parents=True)
    results = [
        _envelope("img_vellin_a"),
        _envelope("img_vellin_b"),
        _envelope("img_vellin_c"),  # not in manifest → must be skipped
    ]
    (batch_dir / "results.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
        encoding="utf-8",
    )

    manifest_path = tmp_path / "manifest.json"
    manifest = Manifest(
        schema_version="0.2.0",
        assets={
            "img_vellin_a": _make_asset("img_vellin_a"),
            "img_vellin_b": _make_asset("img_vellin_b"),
        },
    )
    save_manifest(manifest, manifest_path)

    return {"batch_dir": batch_dir, "manifest_path": manifest_path}


def test_accept_then_reject_writes_two_decisions(review_setup: dict[str, Path]) -> None:
    inputs = iter(["A", "R", "missing reference image quality"])
    viewed: list[str] = []

    written = run_visual_review(
        review_setup["batch_dir"],
        manifest_path=review_setup["manifest_path"],
        viewer=lambda fp: viewed.append(fp),
        input_fn=lambda prompt: next(inputs),
        output=io.StringIO(),
    )

    assert written == 2
    log = (review_setup["batch_dir"] / "visual_review_log.jsonl").read_text()
    rows = [json.loads(line) for line in log.splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["asset_id"] == "img_vellin_a"
    assert rows[0]["accepted"] is True
    assert rows[0]["mechanical_check_passed"] is True
    assert rows[0]["reason"] is None
    assert rows[1]["asset_id"] == "img_vellin_b"
    assert rows[1]["accepted"] is False
    assert rows[1]["reason"] == "missing reference image quality"
    # The viewer must be called for every reviewed asset.
    assert viewed == [
        "content/visuals/vellin/img_vellin_a.png",
        "content/visuals/vellin/img_vellin_b.png",
    ]


def test_skip_writes_no_record(review_setup: dict[str, Path]) -> None:
    inputs = iter(["S", "S"])  # skip both imported assets
    written = run_visual_review(
        review_setup["batch_dir"],
        manifest_path=review_setup["manifest_path"],
        viewer=lambda _: None,
        input_fn=lambda prompt: next(inputs),
        output=io.StringIO(),
    )
    assert written == 0
    assert not (review_setup["batch_dir"] / "visual_review_log.jsonl").exists()


def test_resumable_skips_already_reviewed(review_setup: dict[str, Path]) -> None:
    log_path = review_setup["batch_dir"] / "visual_review_log.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "asset_id": "img_vellin_a",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-02T00:00:00+00:00",
                "mechanical_check_passed": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    inputs = iter(["A"])
    written = run_visual_review(
        review_setup["batch_dir"],
        manifest_path=review_setup["manifest_path"],
        viewer=lambda _: None,
        input_fn=lambda prompt: next(inputs),
        output=io.StringIO(),
    )
    assert written == 1
    rows = [
        json.loads(line) for line in log_path.read_text().splitlines() if line.strip()
    ]
    assert {r["asset_id"] for r in rows} == {"img_vellin_a", "img_vellin_b"}


def test_unimported_asset_is_skipped(review_setup: dict[str, Path]) -> None:
    """img_vellin_c is in results.jsonl but not in the manifest — the CLI
    must surface it in the header but not prompt the author for it."""
    inputs = iter(["A", "A"])  # only the two imported assets

    out = io.StringIO()
    written = run_visual_review(
        review_setup["batch_dir"],
        manifest_path=review_setup["manifest_path"],
        viewer=lambda _: None,
        input_fn=lambda prompt: next(inputs),
        output=out,
    )
    assert written == 2
    text = out.getvalue()
    assert "awaiting import:     1" in text
    assert "pending review:      2" in text


def test_web_path_traversal_is_blocked(tmp_path: Path) -> None:
    """review of T-1.5.8 #3.1: `/../../...` (and url-encoded variants) must
    not escape `serve_root`. We exercise the resolved path mapping rather
    than spinning a real server — the same containment check runs there.
    """
    from generator.visual_review_cli import _start_web_viewer  # noqa: PLC0415

    serve_root = tmp_path / "serve"
    (serve_root / "ok").mkdir(parents=True)
    (serve_root / "ok" / "inside.txt").write_text("hi", encoding="utf-8")
    secret = tmp_path / "outside_secret.txt"
    secret.write_text("BADBADBAD", encoding="utf-8")

    batch_dir = tmp_path / "batch"
    batch_dir.mkdir()
    # Need a results.jsonl + manifest harness to exercise the full path,
    # but for the containment check we just need the handler. Instead we
    # call the inner translate_path indirectly by spawning the viewer
    # against an empty pending list and probing the handler class.
    captured: dict[str, type] = {}

    import socketserver
    import io as _io
    from unittest.mock import patch

    class _NonBindingServer:
        """Drop-in stand-in: capture the handler class without ever opening
        a socket. _start_web_viewer also spawns a thread on `serve_forever`,
        which we make a no-op here."""

        def __init__(self, addr, handler_cls):
            captured["handler_cls"] = handler_cls
            self.server_address = ("127.0.0.1", 0)

        def serve_forever(self) -> None:  # pragma: no cover — no-op
            return None

    with patch.object(socketserver, "TCPServer", _NonBindingServer), patch(
        "webbrowser.open", lambda *a, **kw: True
    ):
        _start_web_viewer(batch_dir, [], serve_root, _io.StringIO())

    handler_cls = captured["handler_cls"]

    class _Recorder:
        def __init__(self) -> None:
            self.errors: list[tuple[int, str]] = []

        def send_error(self, code: int, message: str = "") -> None:
            self.errors.append((code, message))

    # Build an instance bypassing the BaseHTTPRequestHandler constructor.
    inst = handler_cls.__new__(handler_cls)

    serve_root_resolved = serve_root.resolve()
    forbidden_marker = str(serve_root_resolved / "__forbidden__")

    # Each of these must NOT resolve to outside_secret.txt; they must come
    # back as the forbidden marker (which yields 404 in the real server).
    for hostile in (
        "/../outside_secret.txt",
        "/%2e%2e/outside_secret.txt",
        "/ok/../../outside_secret.txt",
        "/ok/../../outside_secret.txt?ignored=1",
        "/ok/../../outside_secret.txt#frag",
    ):
        out = inst.translate_path(hostile)
        assert out == forbidden_marker, (hostile, out)
        # Sanity: the path returned must not point at the secret on disk.
        assert Path(out).resolve() != secret.resolve()

    # Legitimate path inside serve_root still resolves correctly.
    ok = inst.translate_path("/ok/inside.txt")
    assert Path(ok).resolve() == (serve_root_resolved / "ok" / "inside.txt").resolve()

    # Directory listings are blocked.
    rec = _Recorder()
    inst.send_error = rec.send_error  # type: ignore[method-assign]
    assert inst.list_directory(str(serve_root_resolved)) is None
    assert rec.errors and rec.errors[0][0] == 403


def test_index_html_escapes_hostile_manifest_fields(tmp_path: Path) -> None:
    """review of T-1.5.8 #3.1: a malicious manifest entry (e.g. asset_id
    containing `<script>`) must not break out of the rendered HTML.
    """
    from generator.visual_review_cli import _build_index_html  # noqa: PLC0415

    asset = ImageAsset(
        schema_version="0.2.0",
        asset_id="img_safe_id_123",
        asset_kind="character_sheet",
        target_ref="char_<script>alert(1)</script>",
        target_type="character",
        asset_role="character_sheet",
        character_ref="char_<script>alert(1)</script>",
        location_ref=None,
        source_mode="manual",
        format="png",
        width=1024,
        height=1024,
        file_size_bytes=1024,
        has_alpha=True,
        file_path="content/visuals/vellin/img_safe_id_123.png",
        prompt_hash="a" * 64,
        created_at="2026-05-02T00:00:00+00:00",
    )
    html = _build_index_html([({}, asset)])
    # The hostile target_ref must be HTML-escaped, not rendered as a tag.
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    # Img src must be URL-quoted so that path components with reserved
    # chars don't break out of the attribute. The legitimate slashes stay
    # because we explicitly mark `/` as `safe`.
    assert 'src="/content/visuals/vellin/img_safe_id_123.png"' in html


def test_help_smoke() -> None:
    """`python -m generator.visual_review_cli --help` must succeed.

    Defends against module-name drift; STAGE_1.5_TASKS.md T-1.5.8 §2
    explicitly demands this test (GPT-5.5 L2 critique 4.10 — the module
    used to be named `visual_review`).
    """
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "-m", "generator.visual_review_cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--batch-dir" in completed.stdout
    assert "--web" in completed.stdout
