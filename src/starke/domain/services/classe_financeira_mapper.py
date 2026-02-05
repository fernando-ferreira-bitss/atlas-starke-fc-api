"""Mapper for Classe Financeira to CashOut categories."""

from typing import Optional

from starke.core.logging import get_logger
from starke.domain.entities.cash_flow import CashOutCategory

logger = get_logger(__name__)


# Default mapping configuration
# NOTE: These codes may vary by Mega ERP installation
# Update this mapping according to your installation's plano de contas
DEFAULT_CLASSE_MAPPING: dict[str, CashOutCategory] = {
    # OPEX - Operating Expenses (1.2.x codes)
    "1.2.01": CashOutCategory.OPEX,  # Salários e Encargos
    "1.2.02": CashOutCategory.OPEX,  # Manutenção
    "1.2.03": CashOutCategory.OPEX,  # Utilities (água, luz, etc)
    "1.2.04": CashOutCategory.OPEX,  # Marketing
    "1.2.05": CashOutCategory.OPEX,  # Administrativo
    "1.2.06": CashOutCategory.OPEX,  # Serviços Terceirizados

    # CAPEX - Capital Expenditures (1.1.x codes)
    "1.1.01": CashOutCategory.CAPEX,  # Construção Civil
    "1.1.02": CashOutCategory.CAPEX,  # Equipamentos
    "1.1.03": CashOutCategory.CAPEX,  # Melhorias
    "1.1.04": CashOutCategory.CAPEX,  # Aquisição de Ativos

    # FINANCEIRAS - Financial Expenses (1.3.x codes)
    "1.3.01": CashOutCategory.FINANCEIRAS,  # Juros
    "1.3.02": CashOutCategory.FINANCEIRAS,  # Taxas Bancárias
    "1.3.03": CashOutCategory.FINANCEIRAS,  # IOF
    "1.3.04": CashOutCategory.FINANCEIRAS,  # Despesas Financeiras

    # DISTRIBUICOES - Distributions (1.4.x codes)
    "1.4.01": CashOutCategory.DISTRIBUICOES,  # Dividendos
    "1.4.02": CashOutCategory.DISTRIBUICOES,  # Lucros Distribuídos
}


class ClasseFinanceiraMapper:
    """Maps Classe Financeira codes to CashOut categories."""

    def __init__(self, custom_mapping: Optional[dict[str, CashOutCategory]] = None) -> None:
        """
        Initialize mapper.

        Args:
            custom_mapping: Custom mapping to override defaults
        """
        self.mapping = custom_mapping if custom_mapping else DEFAULT_CLASSE_MAPPING.copy()
        logger.info("ClasseFinanceiraMapper initialized", mapping_count=len(self.mapping))

    def map_to_category(self, classe_identificador: Optional[str]) -> CashOutCategory:
        """
        Map Classe Financeira identificador to CashOut category.

        Args:
            classe_identificador: Classe financeira identificador (e.g., "1.2.01")

        Returns:
            CashOutCategory (defaults to OPEX if not found)

        Note:
            If the exact code is not found, tries to match by prefix.
            For example, "1.2.01.001" would match "1.2" pattern for OPEX.
        """
        if not classe_identificador:
            logger.debug("No classe financeira provided, using OPEX as default")
            return CashOutCategory.OPEX

        classe = str(classe_identificador).strip()

        # Try exact match first
        if classe in self.mapping:
            return self.mapping[classe]

        # Try pattern matching by prefix
        # Example: "1.2.01.001" should match "1.2" or "1.2.01"
        for pattern, category in sorted(self.mapping.items(), key=lambda x: len(x[0]), reverse=True):
            if classe.startswith(pattern):
                logger.debug(
                    "Mapped by prefix",
                    classe=classe,
                    pattern=pattern,
                    category=category.value,
                )
                return category

        # Default to OPEX
        logger.warning(
            "Classe financeira not found in mapping, defaulting to OPEX",
            classe=classe,
        )
        return CashOutCategory.OPEX

    def add_mapping(self, classe_identificador: str, category: CashOutCategory) -> None:
        """
        Add or update a mapping.

        Args:
            classe_identificador: Classe financeira identificador
            category: CashOut category
        """
        self.mapping[classe_identificador] = category
        logger.info(
            "Added mapping",
            classe=classe_identificador,
            category=category.value,
        )

    def get_all_mappings(self) -> dict[str, CashOutCategory]:
        """Get all current mappings."""
        return self.mapping.copy()
