from app.utils.redaction import mask_code, mask_email, mask_secret, redact_log_data


def test_mask_secret_preserves_short_prefix_and_suffix() -> None:
    assert mask_secret("abcdefghijklmn") == "ab***mn"


def test_mask_email_hides_local_part() -> None:
    assert mask_email("someone@example.com") == "so***@example.com"


def test_mask_code_hides_full_value() -> None:
    assert mask_code("123456") == "******"


def test_redact_log_data_masks_sensitive_fields_recursively() -> None:
    payload = {
        "email": "user@example.com",
        "refresh_token": "abcd1234efgh5678",
        "nested": {
            "password": "p@ssw0rd",
            "code": "123456",
            "proofId": "proof-123456",
            "items": [
                {"secondary_email": "backup@example.com"},
                {"apiCanary": "canary-secret-value"},
            ],
        },
    }

    redacted = redact_log_data(payload)

    assert redacted["email"] == "us***@example.com"
    assert redacted["refresh_token"] == "ab***78"
    assert redacted["nested"]["password"] == "p@***rd"
    assert redacted["nested"]["code"] == "******"
    assert redacted["nested"]["proofId"] == "pr***56"
    assert redacted["nested"]["items"][0]["secondary_email"] == "ba***@example.com"
    assert redacted["nested"]["items"][1]["apiCanary"] == "ca***ue"
