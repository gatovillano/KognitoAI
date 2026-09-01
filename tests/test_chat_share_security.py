import hashlib

import pytest

from utils.share_link_security import hash_share_link_password, verify_share_link_password


class TestShareLinkPasswordSecurity:
    def test_new_hashes_use_pbkdf2(self):
        hashed = hash_share_link_password("secure-pass-123")
        assert hashed.startswith("pbkdf2_sha256$")

    def test_verify_pbkdf2_password(self):
        hashed = hash_share_link_password("secure-pass-123")
        assert verify_share_link_password("secure-pass-123", hashed)
        assert not verify_share_link_password("wrong-pass", hashed)

    def test_verify_legacy_sha256_password(self):
        legacy = hashlib.sha256("legacy1234".encode()).hexdigest()
        assert verify_share_link_password("legacy1234", legacy)
        assert not verify_share_link_password("wrong", legacy)

    def test_verify_rejects_empty_hash(self):
        assert not verify_share_link_password("anything", "")
