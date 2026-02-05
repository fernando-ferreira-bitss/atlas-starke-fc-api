"""Security utilities for LGPD compliance.

Provides encryption/decryption for sensitive data like CPF/CNPJ.
Uses Fernet symmetric encryption from cryptography library.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load .env file to ensure ENCRYPTION_KEY is available
_env_file = Path(__file__).parents[3] / ".env"
if _env_file.exists():
    load_dotenv(_env_file)


class SecurityService:
    """Service for encrypting/decrypting sensitive data."""

    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize with encryption key.

        Args:
            encryption_key: Base64-encoded 32-byte key for Fernet.
                          If not provided, uses ENCRYPTION_KEY env var.
        """
        key = encryption_key or os.getenv("ENCRYPTION_KEY")
        if not key:
            # Generate a key for development (should be set in production)
            key = Fernet.generate_key().decode()
            os.environ["ENCRYPTION_KEY"] = key

        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, data: str) -> str:
        """Encrypt a string.

        Args:
            data: Plain text to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if not data:
            return ""
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string.

        Args:
            encrypted_data: Encrypted string (base64 encoded)

        Returns:
            Decrypted plain text
        """
        if not encrypted_data:
            return ""
        return self._fernet.decrypt(encrypted_data.encode()).decode()

    @staticmethod
    def hash_for_search(data: str) -> str:
        """Create a hash for searchable encrypted fields.

        This allows searching without decrypting all records.
        Uses SHA-256 for consistent hashing.

        Args:
            data: Plain text to hash

        Returns:
            SHA-256 hash as hex string
        """
        if not data:
            return ""
        # Normalize: remove non-digits for CPF/CNPJ
        normalized = "".join(c for c in data if c.isdigit())
        return hashlib.sha256(normalized.encode()).hexdigest()


# Global instance (lazy initialization)
_security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """Get or create the global security service instance."""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service


def normalize_cpf_cnpj(cpf_cnpj: str) -> str:
    """Remove formatting from CPF/CNPJ, keeping only digits.

    Args:
        cpf_cnpj: CPF or CNPJ (can have formatting like 123.456.789-01)

    Returns:
        Only digits (e.g., 12345678901)
    """
    return "".join(c for c in cpf_cnpj if c.isdigit())


def encrypt_cpf_cnpj(cpf_cnpj: str) -> tuple[str, str]:
    """Encrypt CPF/CNPJ and return both encrypted value and hash.

    The CPF/CNPJ is normalized (mask removed) before encryption.

    Args:
        cpf_cnpj: CPF or CNPJ (can have formatting)

    Returns:
        Tuple of (encrypted_value, search_hash)
    """
    service = get_security_service()
    # Normalize: remove mask before encrypting
    normalized = normalize_cpf_cnpj(cpf_cnpj)
    encrypted = service.encrypt(normalized)
    hash_value = service.hash_for_search(cpf_cnpj)
    return encrypted, hash_value


def decrypt_cpf_cnpj(encrypted: str) -> str:
    """Decrypt CPF/CNPJ.

    Args:
        encrypted: Encrypted CPF/CNPJ

    Returns:
        Decrypted plain text CPF/CNPJ
    """
    service = get_security_service()
    return service.decrypt(encrypted)
