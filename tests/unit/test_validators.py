"""Tests for CPF/CNPJ validators."""

import pytest

from starke.api.v1.clients.schemas import (
    validate_cpf_cnpj,
    _validate_cpf,
    _validate_cnpj,
)


class TestValidateCpf:
    """Tests for CPF validation."""

    def test_valid_cpf_without_formatting(self):
        """Test that valid CPF without formatting passes."""
        # Valid CPFs (verified with checksum algorithm)
        assert _validate_cpf("12345678909") is True
        assert _validate_cpf("52998224725") is True
        assert _validate_cpf("98765432100") is True

    def test_invalid_cpf_wrong_checksum(self):
        """Test that CPF with wrong checksum fails."""
        assert _validate_cpf("12345678901") is False
        assert _validate_cpf("12345678900") is False

    def test_cpf_all_same_digits(self):
        """Test that CPF with all same digits is invalid."""
        assert _validate_cpf("00000000000") is False
        assert _validate_cpf("11111111111") is False
        assert _validate_cpf("22222222222") is False
        assert _validate_cpf("99999999999") is False

    def test_cpf_wrong_length(self):
        """Test that CPF with wrong length is invalid."""
        assert _validate_cpf("1234567890") is False  # 10 digits
        assert _validate_cpf("123456789012") is False  # 12 digits
        assert _validate_cpf("") is False

    def test_cpf_first_digit_calculation(self):
        """Test CPF first verification digit calculation."""
        # CPF: 123.456.789-09
        # First digit: sum of (1*10 + 2*9 + 3*8 + 4*7 + 5*6 + 6*5 + 7*4 + 8*3 + 9*2) = 210
        # 210 % 11 = 1, 11 - 1 = 10 -> 0
        assert _validate_cpf("12345678909") is True


class TestValidateCnpj:
    """Tests for CNPJ validation."""

    def test_valid_cnpj_without_formatting(self):
        """Test that valid CNPJ without formatting passes."""
        # Valid CNPJs
        assert _validate_cnpj("11222333000181") is True
        assert _validate_cnpj("11444777000161") is True

    def test_invalid_cnpj_wrong_checksum(self):
        """Test that CNPJ with wrong checksum fails."""
        assert _validate_cnpj("11222333000182") is False
        assert _validate_cnpj("11222333000180") is False

    def test_cnpj_all_same_digits(self):
        """Test that CNPJ with all same digits is invalid."""
        assert _validate_cnpj("00000000000000") is False
        assert _validate_cnpj("11111111111111") is False
        assert _validate_cnpj("99999999999999") is False

    def test_cnpj_wrong_length(self):
        """Test that CNPJ with wrong length is invalid."""
        assert _validate_cnpj("1122233300018") is False  # 13 digits
        assert _validate_cnpj("112223330001811") is False  # 15 digits
        assert _validate_cnpj("") is False


class TestValidateCpfCnpj:
    """Tests for validate_cpf_cnpj function."""

    def test_valid_cpf_with_formatting(self):
        """Test that valid CPF with formatting passes."""
        result = validate_cpf_cnpj("123.456.789-09")
        assert result == "123.456.789-09"

    def test_valid_cpf_without_formatting(self):
        """Test that valid CPF without formatting passes."""
        result = validate_cpf_cnpj("12345678909")
        assert result == "12345678909"

    def test_valid_cnpj_with_formatting(self):
        """Test that valid CNPJ with formatting passes."""
        result = validate_cpf_cnpj("11.222.333/0001-81")
        assert result == "11.222.333/0001-81"

    def test_valid_cnpj_without_formatting(self):
        """Test that valid CNPJ without formatting passes."""
        result = validate_cpf_cnpj("11222333000181")
        assert result == "11222333000181"

    def test_invalid_cpf_raises(self):
        """Test that invalid CPF raises ValueError."""
        with pytest.raises(ValueError, match="CPF inválido"):
            validate_cpf_cnpj("12345678901")

    def test_invalid_cnpj_raises(self):
        """Test that invalid CNPJ raises ValueError."""
        with pytest.raises(ValueError, match="CNPJ inválido"):
            validate_cpf_cnpj("11222333000182")

    def test_wrong_length_raises(self):
        """Test that wrong length raises ValueError."""
        with pytest.raises(ValueError, match="11 dígitos ou CNPJ deve ter 14"):
            validate_cpf_cnpj("1234567890")  # 10 digits

        with pytest.raises(ValueError, match="11 dígitos ou CNPJ deve ter 14"):
            validate_cpf_cnpj("1234567890123")  # 13 digits

    def test_empty_string_raises(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            validate_cpf_cnpj("")

    def test_letters_removed(self):
        """Test that non-digit characters are removed for validation."""
        # This should work because letters are removed
        result = validate_cpf_cnpj("123.456.789-09")
        assert result == "123.456.789-09"


class TestKnownValidDocuments:
    """Tests with known valid CPF/CNPJ for regression."""

    @pytest.mark.parametrize("cpf", [
        "52998224725",
        "12345678909",
        "98765432100",
        "39053344705",  # Valid CPF verified with checksum
    ])
    def test_known_valid_cpfs(self, cpf):
        """Test known valid CPFs pass validation."""
        assert _validate_cpf(cpf) is True

    @pytest.mark.parametrize("cnpj", [
        "11222333000181",
        "11444777000161",
    ])
    def test_known_valid_cnpjs(self, cnpj):
        """Test known valid CNPJs pass validation."""
        assert _validate_cnpj(cnpj) is True
