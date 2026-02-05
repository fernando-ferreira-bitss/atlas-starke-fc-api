"""Configuration loader for Mega API mapping."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class MegaMappingConfig:
    """Load and provide access to Mega API mapping configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            # Default location: project_root/config/mega_mapping.yaml
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "mega_mapping.yaml"

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"Please create the file based on config/mega_mapping.yaml.example"
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()

    # ============================================
    # Cash Out Categories
    # ============================================

    def get_cash_out_category(self, classe_financeira: str) -> str:
        """
        Get Starke cash out category for a Mega financial class.

        Args:
            classe_financeira: Mega financial class code (e.g., "1.2.01")

        Returns:
            Category name: "opex", "capex", "financeiras", "distribuicoes", or "outras"
        """
        categories = self._config.get("cash_out_categories", {})

        for category, classes in categories.items():
            if classe_financeira in classes:
                return category

        return "outras"  # Default for unmapped classes

    def get_cash_out_category_by_tipo_documento(self, tipo_documento: str) -> str:
        """
        Get Starke cash out category for a Mega TipoDocumento.

        Args:
            tipo_documento: Mega document type (e.g., "DISTRATO", "NOTA FISCAL")

        Returns:
            Category name: "opex", "capex", "financeiras", "distribuicoes", or "outras"
        """
        categories = self._config.get("tipo_documento_categories", {})

        # Normalize tipo_documento to uppercase for matching
        tipo_documento_upper = tipo_documento.upper() if tipo_documento else ""

        for category, tipos in categories.items():
            if tipo_documento_upper in [t.upper() for t in tipos]:
                return category

        return "outras"  # Default for unmapped document types

    def get_opex_classes(self) -> List[str]:
        """Get list of financial classes mapped to OPEX."""
        return self._config.get("cash_out_categories", {}).get("opex", [])

    def get_capex_classes(self) -> List[str]:
        """Get list of financial classes mapped to CAPEX."""
        return self._config.get("cash_out_categories", {}).get("capex", [])

    def get_financeiras_classes(self) -> List[str]:
        """Get list of financial classes mapped to financial expenses."""
        return self._config.get("cash_out_categories", {}).get("financeiras", [])

    def get_distribuicoes_classes(self) -> List[str]:
        """Get list of financial classes mapped to distributions."""
        return self._config.get("cash_out_categories", {}).get("distribuicoes", [])

    # ============================================
    # Cash In Categories
    # ============================================

    def get_cash_in_category(self, classe_financeira: str) -> str:
        """
        Get Starke cash in category for a Mega financial class.

        Args:
            classe_financeira: Mega financial class code

        Returns:
            Category name: "outras" (for non-contract revenues)
        """
        categories = self._config.get("cash_in_categories", {})

        for category, classes in categories.items():
            if classe_financeira in classes:
                return category

        return None  # None means it's not "outras", likely from contracts

    def get_outras_receitas_classes(self) -> List[str]:
        """Get list of financial classes for other revenues (non-contracts)."""
        return self._config.get("cash_in_categories", {}).get("outras", [])

    # ============================================
    # Disponibilidades (Cash & Bank Accounts)
    # ============================================

    def get_contas_disponibilidades(self) -> List[str]:
        """Get list of account codes representing cash and bank accounts."""
        return self._config.get("contas_disponibilidades", [])

    def is_conta_disponibilidade(self, conta_codigo: str) -> bool:
        """
        Check if an account code is a cash/bank account.

        Args:
            conta_codigo: Account code to check

        Returns:
            True if it's a cash/bank account
        """
        return conta_codigo in self.get_contas_disponibilidades()

    # ============================================
    # Empreendimento Mapping
    # ============================================

    def get_empreendimento_mapping(self, empreendimento_id: int) -> Optional[Dict[str, int]]:
        """
        Get filial/centro_custo mapping for an empreendimento.

        Args:
            empreendimento_id: Empreendimento ID

        Returns:
            Dict with filial, centro_custo, projeto, or None if not mapped
        """
        mapping = self._config.get("empreendimento_mapping", {})
        return mapping.get(empreendimento_id)

    # ============================================
    # Financial Settings
    # ============================================

    def get_taxa_desconto(self, empreendimento_id: Optional[int] = None) -> float:
        """
        Get discount rate for duration calculation.

        Args:
            empreendimento_id: Optional empreendimento ID for specific rate

        Returns:
            Discount rate (e.g., 0.10 for 10%)
        """
        financeiro = self._config.get("financeiro", {})

        if empreendimento_id is not None:
            specific_rates = financeiro.get("taxa_desconto_por_empreendimento", {})
            if empreendimento_id in specific_rates:
                return specific_rates[empreendimento_id]

        return financeiro.get("taxa_desconto_padrao", 0.10)

    def get_prazo_minimo_vp_dias(self) -> int:
        """Get minimum days overdue to include in VP calculation."""
        return self._config.get("financeiro", {}).get("prazo_minimo_vp_dias", -365)

    # ============================================
    # Integration Settings
    # ============================================

    def get_periodo_inicial_meses(self) -> int:
        """Get initial sync period in months."""
        return self._config.get("integracao", {}).get("periodo_inicial_meses", 12)

    def get_janela_sincronizacao_dias(self) -> int:
        """Get sync window in days for incremental sync."""
        return self._config.get("integracao", {}).get("janela_sincronizacao_dias", 7)

    def get_timeout_api_segundos(self) -> int:
        """Get API call timeout in seconds."""
        return self._config.get("integracao", {}).get("timeout_api_segundos", 60)

    def get_max_retries(self) -> int:
        """Get maximum number of retries for API calls."""
        return self._config.get("integracao", {}).get("max_retries", 3)

    def get_retry_delay_segundos(self) -> int:
        """Get delay between retries in seconds."""
        return self._config.get("integracao", {}).get("retry_delay_segundos", 5)

    def get_batch_size(self) -> int:
        """Get batch size for processing records."""
        return self._config.get("integracao", {}).get("batch_size", 100)

    # ============================================
    # Validations
    # ============================================

    def get_status_contrato_ativo(self) -> List[str]:
        """Get list of contract statuses considered active."""
        return self._config.get("validacoes", {}).get("status_contrato_ativo", ["A", "N"])

    def get_status_parcela_a_receber(self) -> List[str]:
        """Get list of installment statuses considered receivable."""
        return self._config.get("validacoes", {}).get("status_parcela_a_receber", ["A", "P"])

    def get_status_parcela_pago(self) -> List[str]:
        """Get list of installment statuses considered paid."""
        return self._config.get("validacoes", {}).get("status_parcela_pago", ["Q", "L"])

    def is_contrato_ativo(self, status: str) -> bool:
        """
        Check if contract status is considered active.

        Supports both old API format (short codes: "A", "N") and new API format
        (full strings: "Ativo", "Normal").
        """
        if not status:
            return False

        # Mapping from full status names to short codes
        status_mapping = {
            "Ativo": "A",
            "Normal": "N",
            "Inadimplente": "I",  # Not active
            "Quitado": "Q",  # Not active
            "Distratado": "D",  # Not active
        }

        # Get normalized status (convert full name to short code if needed)
        normalized_status = status_mapping.get(status, status)

        return normalized_status in self.get_status_contrato_ativo()

    def is_parcela_a_receber(self, status: str) -> bool:
        """Check if installment status is considered receivable."""
        return status in self.get_status_parcela_a_receber()

    def is_parcela_pago(self, status: str) -> bool:
        """Check if installment status is considered paid."""
        return status in self.get_status_parcela_pago()

    # ============================================
    # Logging
    # ============================================

    def get_log_level(self) -> str:
        """Get logging level."""
        return self._config.get("logging", {}).get("level", "INFO")

    def should_log_api_calls(self) -> bool:
        """Check if API calls should be logged."""
        return self._config.get("logging", {}).get("log_api_calls", True)

    def should_log_transformed_data(self) -> bool:
        """Check if transformed data should be logged."""
        return self._config.get("logging", {}).get("log_transformed_data", False)

    def get_audit_log_path(self) -> str:
        """Get path for audit log file."""
        return self._config.get("logging", {}).get("audit_log_path", "logs/mega_sync_audit.log")


# Singleton instance
_config_instance: Optional[MegaMappingConfig] = None


def get_mega_config(config_path: Optional[str] = None) -> MegaMappingConfig:
    """
    Get singleton instance of MegaMappingConfig.

    Args:
        config_path: Optional path to config file

    Returns:
        MegaMappingConfig instance
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = MegaMappingConfig(config_path)

    return _config_instance


def reload_mega_config() -> None:
    """Reload configuration from file."""
    global _config_instance

    if _config_instance is not None:
        _config_instance.reload()
