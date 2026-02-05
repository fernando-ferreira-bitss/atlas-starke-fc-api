"""Integration tests for ingestion service with mocked API."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from starke.domain.services.ingestion_service import IngestionService
from starke.infrastructure.external_apis.mega_client import MegaAPIClient


class TestIngestionService:
    """Integration tests for IngestionService."""

    @patch.object(MegaAPIClient, "get_contratos_by_empreendimento")
    def test_ingest_contratos_with_idempotency(
        self, mock_get_contratos, db_session, sample_contrato_data
    ):
        """Test contract ingestion with idempotency check."""
        # Setup mock
        mock_get_contratos.return_value = [sample_contrato_data]

        # Create mock API client
        api_client = MagicMock(spec=MegaAPIClient)
        api_client.get_contratos_by_empreendimento = mock_get_contratos

        service = IngestionService(db_session, api_client)

        # First ingestion
        contratos_1 = service.ingest_contratos_by_empreendimento(
            empreendimento_id=5678, exec_date=date(2024, 1, 31)
        )

        assert len(contratos_1) == 1
        assert contratos_1[0]["codigoContrato"] == 1234

        # Second ingestion with same data (should be idempotent)
        contratos_2 = service.ingest_contratos_by_empreendimento(
            empreendimento_id=5678, exec_date=date(2024, 1, 31)
        )

        assert len(contratos_2) == 1
        # Verify API was only called once due to idempotency
        assert mock_get_contratos.call_count == 2  # Called but data recognized as duplicate

    @patch.object(MegaAPIClient, "get_parcelas_by_contrato")
    def test_ingest_parcelas(self, mock_get_parcelas, db_session, sample_parcela_data):
        """Test installment ingestion."""
        # Setup mock
        mock_get_parcelas.return_value = [sample_parcela_data]

        api_client = MagicMock(spec=MegaAPIClient)
        api_client.get_parcelas_by_contrato = mock_get_parcelas

        service = IngestionService(db_session, api_client)

        parcelas = service.ingest_parcelas_by_contrato(
            contrato_id=1234, exec_date=date(2024, 1, 31)
        )

        assert len(parcelas) == 1
        assert parcelas[0]["codigoParcela"] == 1
        assert parcelas[0]["status"] == "pago"

    @patch.object(MegaAPIClient, "get_contratos_by_empreendimento")
    @patch.object(MegaAPIClient, "get_parcelas_by_contrato")
    def test_ingest_all_for_date(
        self,
        mock_get_parcelas,
        mock_get_contratos,
        db_session,
        sample_contrato_data,
        sample_parcela_data,
    ):
        """Test full ingestion for multiple empreendimentos."""
        # Setup mocks
        mock_get_contratos.return_value = [sample_contrato_data]
        mock_get_parcelas.return_value = [sample_parcela_data]

        api_client = MagicMock(spec=MegaAPIClient)
        api_client.get_contratos_by_empreendimento = mock_get_contratos
        api_client.get_parcelas_by_contrato = mock_get_parcelas

        service = IngestionService(db_session, api_client)

        summary = service.ingest_all_for_date(
            empreendimento_ids=[5678, 5679], exec_date=date(2024, 1, 31)
        )

        assert summary["total_contracts"] == 2  # 1 contract per empreendimento
        assert summary["total_installments"] == 2  # 1 installment per contract
        assert len(summary["empreendimentos"]) == 2
        assert len(summary["errors"]) == 0
