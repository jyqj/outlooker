from __future__ import annotations

from pathlib import Path

from app.services.outlook.protocol_parsers import (
    _extract_api_canary,
    _extract_arr_user_proofs,
    _extract_canary,
    _extract_continue_form,
    _extract_email_proofs,
    _extract_flow_token,
    _extract_ppft,
    _extract_url_post,
    _extract_verify_proof_action,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "outlook_protocol"


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_extract_login_page_tokens():
    html = _read("protocol_phase1_login_success.html")
    assert _extract_ppft(html) == "ppft-token-sample"
    assert _extract_url_post(html) == "https://login.live.com/ppsecure/post.srf"
    assert _extract_flow_token(html) == "flow-token-sample"


def test_extract_proofs_page_tokens_and_arrays():
    html = _read("protocol_phase2_proofs_manage_success.html")
    assert _extract_api_canary(html) == "api-canary-sample"
    proofs = _extract_arr_user_proofs(html)
    email_proofs = _extract_email_proofs(html)
    assert proofs[0]["data"] == "proof-data-1"
    assert email_proofs[0]["displayProofId"] == "recovery@example.com"


def test_extract_canary_and_verify_action():
    html = _read("protocol_phase3_add_proof_success.html")
    assert _extract_canary(html) == "canary-sample"
    assert _extract_verify_proof_action(html) == "https://account.live.com/proofs/Add"


def test_extract_continue_form():
    html = """
    <html><body>
      <form action="https://example.com/continue">
        <input name="foo" value="bar" />
      </form>
    </body></html>
    """
    form = _extract_continue_form(html)
    assert form is not None
    assert form["action"] == "https://example.com/continue"
    assert form["inputs"]["foo"] == "bar"
