"""Service for managing developments (real estate projects)."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from starke.infrastructure.database.models import Development
from starke.infrastructure.external_apis.mega_client import MegaAPIClient


class DevelopmentService:
    """Service for managing developments."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def get_all_developments(self, active_only: bool = False, origem: Optional[str] = None) -> List[Development]:
        """Get all developments from database."""
        query = self.db.query(Development)
        if active_only:
            query = query.filter(Development.is_active == True)  # noqa: E712
        if origem:
            query = query.filter(Development.origem == origem)
        return query.order_by(Development.name).all()

    def get_development_by_id(self, development_id: int) -> Optional[Development]:
        """Get development by ID."""
        return self.db.query(Development).filter(Development.id == development_id).first()

    def activate_development(self, development_id: int) -> Optional[Development]:
        """Activate a development."""
        dev = self.get_development_by_id(development_id)
        if dev:
            dev.is_active = True
            dev.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(dev)
        return dev

    def deactivate_development(self, development_id: int) -> Optional[Development]:
        """Deactivate a development."""
        dev = self.get_development_by_id(development_id)
        if dev:
            dev.is_active = False
            dev.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(dev)
        return dev

    def sync_from_mega_api(self) -> dict:
        """
        Sync developments from Mega API.

        Returns:
            Summary with counts of created, updated, and errors
        """
        summary = {
            "created": 0,
            "updated": 0,
            "total": 0,
            "errors": [],
        }

        try:
            with MegaAPIClient() as api_client:
                # Fetch developments from API
                api_developments = api_client.get_empreendimentos()

                for api_dev in api_developments:
                    try:
                        # Try to get ID from different possible fields
                        dev_id = api_dev.get("codigo") or api_dev.get("est_in_codigo")

                        # Try to get name from different possible fields
                        dev_name = (
                            api_dev.get("nome")
                            or api_dev.get("est_st_nome")
                            or api_dev.get("descricao")
                            or f"Development {dev_id}"
                        )

                        if not dev_id:
                            summary["errors"].append(f"Development without ID skipped: {api_dev}")
                            continue

                        # Filtrar empreendimentos de teste ou simulação
                        dev_name_upper = dev_name.upper()
                        if "TESTE" in dev_name_upper or dev_name_upper == "SIMULAÇÃO":
                            continue  # Ignora empreendimentos de teste/simulação

                        # Convert to int if needed
                        dev_id = int(dev_id) if not isinstance(dev_id, int) else dev_id

                        # Extract centro de custo (cost center) ID
                        centro_custo_id = None
                        if "centroCusto" in api_dev and isinstance(api_dev["centroCusto"], dict):
                            centro_custo_id = api_dev["centroCusto"].get("reduzido")
                            if centro_custo_id:
                                centro_custo_id = int(centro_custo_id) if not isinstance(centro_custo_id, int) else centro_custo_id

                        # Check if exists
                        existing = self.get_development_by_id(dev_id)

                        if existing:
                            # Update existing
                            existing.name = dev_name
                            existing.centro_custo_id = centro_custo_id
                            existing.raw_data = api_dev
                            existing.is_active = False  # Reset to inactive, will be activated by contract sync
                            existing.last_synced_at = datetime.now(timezone.utc)
                            existing.updated_at = datetime.now(timezone.utc)
                            summary["updated"] += 1
                        else:
                            # Create new
                            new_dev = Development(
                                id=dev_id,
                                name=dev_name,
                                centro_custo_id=centro_custo_id,
                                is_active=False,  # Default to inactive, will be activated by contract sync
                                raw_data=api_dev,
                                last_synced_at=datetime.now(timezone.utc),
                            )
                            self.db.add(new_dev)
                            summary["created"] += 1

                        summary["total"] += 1

                    except Exception as e:
                        error_msg = f"Error processing development {api_dev.get('id')}: {str(e)}"
                        summary["errors"].append(error_msg)

                self.db.commit()

        except Exception as e:
            error_msg = f"Error syncing from Mega API: {str(e)}"
            summary["errors"].append(error_msg)
            self.db.rollback()

        return summary
