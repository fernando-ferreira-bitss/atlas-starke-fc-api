"""Tests for security utilities (encryption/decryption)."""

import pytest
from cryptography.fernet import InvalidToken

from starke.core.security import (
    SecurityService,
    encrypt_cpf_cnpj,
    decrypt_cpf_cnpj,
    get_security_service,
)


class TestSecurityService:
    """Tests for SecurityService class."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption returns the original value."""
        service = SecurityService()
        original = "12345678909"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original
        assert encrypted != original

    def test_encrypt_empty_string(self):
        """Test that empty string returns empty string."""
        service = SecurityService()

        encrypted = service.encrypt("")
        decrypted = service.decrypt("")

        assert encrypted == ""
        assert decrypted == ""

    def test_encrypt_different_outputs(self):
        """Test that same input produces different encrypted outputs (due to IV)."""
        service = SecurityService()
        original = "12345678909"

        encrypted1 = service.encrypt(original)
        encrypted2 = service.encrypt(original)

        # Fernet uses different IVs, so outputs should be different
        assert encrypted1 != encrypted2
        # But both should decrypt to the same value
        assert service.decrypt(encrypted1) == original
        assert service.decrypt(encrypted2) == original

    def test_hash_for_search_consistency(self):
        """Test that same input always produces the same hash."""
        service = SecurityService()

        hash1 = service.hash_for_search("12345678909")
        hash2 = service.hash_for_search("12345678909")

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars

    def test_hash_removes_formatting(self):
        """Test that hash normalizes input by removing non-digits."""
        service = SecurityService()

        # CPF with formatting
        hash_formatted = service.hash_for_search("123.456.789-09")
        # CPF without formatting
        hash_plain = service.hash_for_search("12345678909")

        assert hash_formatted == hash_plain

    def test_hash_cnpj_removes_formatting(self):
        """Test that hash normalizes CNPJ by removing non-digits."""
        service = SecurityService()

        # CNPJ with formatting
        hash_formatted = service.hash_for_search("12.345.678/0001-90")
        # CNPJ without formatting
        hash_plain = service.hash_for_search("12345678000190")

        assert hash_formatted == hash_plain

    def test_hash_empty_string(self):
        """Test that empty string returns empty hash."""
        service = SecurityService()

        result = service.hash_for_search("")

        assert result == ""

    def test_decrypt_invalid_data_raises(self):
        """Test that decrypting invalid data raises InvalidToken."""
        service = SecurityService()

        with pytest.raises(InvalidToken):
            service.decrypt("invalid_encrypted_data")

    def test_decrypt_corrupted_data_raises(self):
        """Test that decrypting corrupted data raises InvalidToken."""
        service = SecurityService()
        original = "12345678909"

        encrypted = service.encrypt(original)
        # Corrupt the encrypted data
        corrupted = encrypted[:-5] + "xxxxx"

        with pytest.raises(InvalidToken):
            service.decrypt(corrupted)


class TestEncryptCpfCnpj:
    """Tests for encrypt_cpf_cnpj helper function."""

    def test_returns_tuple(self):
        """Test that function returns a tuple of (encrypted, hash)."""
        result = encrypt_cpf_cnpj("12345678909")

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_encrypted_not_original(self):
        """Test that encrypted value is different from original."""
        cpf = "12345678909"
        encrypted, hash_value = encrypt_cpf_cnpj(cpf)

        assert encrypted != cpf

    def test_hash_is_consistent(self):
        """Test that same CPF produces same hash."""
        cpf = "12345678909"

        _, hash1 = encrypt_cpf_cnpj(cpf)
        _, hash2 = encrypt_cpf_cnpj(cpf)

        assert hash1 == hash2

    def test_cnpj_encryption(self):
        """Test that CNPJ can be encrypted."""
        cnpj = "12345678000190"
        encrypted, hash_value = encrypt_cpf_cnpj(cnpj)

        assert encrypted != cnpj
        assert len(hash_value) == 64


class TestDecryptCpfCnpj:
    """Tests for decrypt_cpf_cnpj helper function."""

    def test_decrypt_returns_original(self):
        """Test that decrypt returns original CPF."""
        cpf = "12345678909"
        encrypted, _ = encrypt_cpf_cnpj(cpf)

        decrypted = decrypt_cpf_cnpj(encrypted)

        assert decrypted == cpf

    def test_decrypt_cnpj_returns_original(self):
        """Test that decrypt returns original CNPJ."""
        cnpj = "12345678000190"
        encrypted, _ = encrypt_cpf_cnpj(cnpj)

        decrypted = decrypt_cpf_cnpj(encrypted)

        assert decrypted == cnpj

    def test_decrypt_formatted_cpf(self):
        """Test that decrypt returns formatted CPF if that was encrypted."""
        cpf = "123.456.789-09"
        encrypted, _ = encrypt_cpf_cnpj(cpf)

        decrypted = decrypt_cpf_cnpj(encrypted)

        assert decrypted == cpf


class TestGetSecurityService:
    """Tests for get_security_service singleton."""

    def test_returns_same_instance(self):
        """Test that get_security_service returns the same instance."""
        service1 = get_security_service()
        service2 = get_security_service()

        assert service1 is service2

    def test_instance_works(self):
        """Test that the singleton instance works correctly."""
        service = get_security_service()
        original = "test_data"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original
