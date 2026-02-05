"""Pytest configuration and fixtures."""

from datetime import datetime
from decimal import Decimal
from typing import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from starke.api.main import app
from starke.api.dependencies import get_db
from starke.core.security import encrypt_cpf_cnpj
from starke.domain.services.auth_service import AuthService
from starke.infrastructure.database.base import Base
from starke.infrastructure.database.models import User, UserRole
from starke.infrastructure.database.patrimony.institution import PatInstitution
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.account import PatAccount
from starke.infrastructure.database.patrimony.asset import PatAsset
from starke.infrastructure.database.patrimony.liability import PatLiability


# =============================================================================
# Database Fixtures
# =============================================================================

from sqlalchemy.pool import StaticPool

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a test database session using SQLite in-memory with shared cache."""
    # Using SQLite in-memory with shared cache for multiple connections
    test_db_url = "sqlite:///:memory:"

    engine = create_engine(
        test_db_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Single connection pool for shared in-memory DB
    )

    # Create all tables
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()

    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # Clean up tables after each test
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# User Fixtures by Role
# =============================================================================

@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an admin user."""
    user = User(
        email="admin@test.com",
        hashed_password=AuthService.get_password_hash("Admin@123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        role=UserRole.ADMIN.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def rm_user(db_session: Session) -> User:
    """Create a Relationship Manager user."""
    user = User(
        email="rm@test.com",
        hashed_password=AuthService.get_password_hash("Rm@123456"),
        full_name="RM User",
        is_active=True,
        is_superuser=False,
        role=UserRole.RM.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def analyst_user(db_session: Session) -> User:
    """Create an Analyst user."""
    user = User(
        email="analyst@test.com",
        hashed_password=AuthService.get_password_hash("Analyst@123"),
        full_name="Analyst User",
        is_active=True,
        is_superuser=False,
        role=UserRole.ANALYST.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client_user(db_session: Session) -> User:
    """Create a Client user."""
    user = User(
        email="client@test.com",
        hashed_password=AuthService.get_password_hash("Client@123"),
        full_name="Client User",
        is_active=True,
        is_superuser=False,
        role=UserRole.CLIENT.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session) -> User:
    """Create an inactive user."""
    user = User(
        email="inactive@test.com",
        hashed_password=AuthService.get_password_hash("Inactive@123"),
        full_name="Inactive User",
        is_active=False,
        is_superuser=False,
        role=UserRole.ANALYST.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# =============================================================================
# Token Fixtures
# =============================================================================

@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generate JWT token for admin user."""
    return AuthService.create_access_token(data={"sub": admin_user.email})


@pytest.fixture
def rm_token(rm_user: User) -> str:
    """Generate JWT token for RM user."""
    return AuthService.create_access_token(data={"sub": rm_user.email})


@pytest.fixture
def analyst_token(analyst_user: User) -> str:
    """Generate JWT token for Analyst user."""
    return AuthService.create_access_token(data={"sub": analyst_user.email})


@pytest.fixture
def client_token(client_user: User) -> str:
    """Generate JWT token for Client user."""
    return AuthService.create_access_token(data={"sub": client_user.email})


def auth_headers(token: str) -> dict:
    """Helper to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Patrimony Fixtures
# =============================================================================

@pytest.fixture
def sample_institution(db_session: Session) -> PatInstitution:
    """Create a sample institution."""
    institution = PatInstitution(
        id=str(uuid4()),
        name="Banco Teste",
        code="001",
        institution_type="bank",
        is_active=True,
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    return institution


@pytest.fixture
def sample_client(db_session: Session, rm_user: User) -> PatClient:
    """Create a sample patrimony client."""
    cpf = "12345678909"  # Valid CPF
    encrypted, hash_value = encrypt_cpf_cnpj(cpf)

    pat_client = PatClient(
        id=str(uuid4()),
        name="Cliente Teste",
        client_type="pf",
        cpf_cnpj_encrypted=encrypted,
        cpf_cnpj_hash=hash_value,
        email="cliente.teste@email.com",
        phone="11999999999",
        status="active",
        base_currency="BRL",
        rm_user_id=rm_user.id,
    )
    db_session.add(pat_client)
    db_session.commit()
    db_session.refresh(pat_client)
    return pat_client


@pytest.fixture
def sample_client_with_user(
    db_session: Session, rm_user: User, client_user: User
) -> PatClient:
    """Create a patrimony client linked to a user (for client login)."""
    cpf = "98765432100"  # Valid CPF
    encrypted, hash_value = encrypt_cpf_cnpj(cpf)

    pat_client = PatClient(
        id=str(uuid4()),
        name="Cliente com Login",
        client_type="pf",
        cpf_cnpj_encrypted=encrypted,
        cpf_cnpj_hash=hash_value,
        email="cliente.login@email.com",
        phone="11988888888",
        status="active",
        base_currency="BRL",
        rm_user_id=rm_user.id,
        user_id=client_user.id,
    )
    db_session.add(pat_client)
    db_session.commit()
    db_session.refresh(pat_client)
    return pat_client


@pytest.fixture
def sample_account(
    db_session: Session, sample_client: PatClient, sample_institution: PatInstitution
) -> PatAccount:
    """Create a sample account."""
    account = PatAccount(
        id=str(uuid4()),
        client_id=sample_client.id,
        institution_id=sample_institution.id,
        account_type="checking",
        account_number="12345-6",
        agency="0001",
        currency="BRL",
        is_active=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def sample_asset(
    db_session: Session, sample_client: PatClient, sample_account: PatAccount
) -> PatAsset:
    """Create a sample asset."""
    asset = PatAsset(
        id=str(uuid4()),
        client_id=sample_client.id,
        account_id=sample_account.id,
        category="renda_fixa",
        subcategory="CDB",
        name="CDB Banco Teste",
        description="CDB 100% CDI",
        base_value=Decimal("10000.00"),
        current_value=Decimal("10500.00"),
        quantity=Decimal("1"),
        currency="BRL",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def sample_liability(
    db_session: Session, sample_client: PatClient, sample_institution: PatInstitution
) -> PatLiability:
    """Create a sample liability."""
    liability = PatLiability(
        id=str(uuid4()),
        client_id=sample_client.id,
        institution_id=sample_institution.id,
        liability_type="personal_loan",
        description="Empréstimo Pessoal",
        original_amount=Decimal("50000.00"),
        current_balance=Decimal("45000.00"),
        monthly_payment=Decimal("1500.00"),
        interest_rate=Decimal("1.5"),
        currency="BRL",
        is_active=True,
    )
    db_session.add(liability)
    db_session.commit()
    db_session.refresh(liability)
    return liability


# =============================================================================
# Legacy Fixtures (existing)
# =============================================================================

@pytest.fixture
def sample_contrato_data() -> dict:
    """Sample contract data for testing."""
    return {
        "codigoContrato": 1234,
        "codigoEmpreendimento": 5678,
        "nomeEmpreendimento": "Test Empreendimento",
        "cpfCnpj": "12345678901",
        "nomeCliente": "Test Client",
        "valorContrato": 100000.00,
        "dataContrato": "2024-01-01",
        "status": "ativo",
        "numeroParcelas": 12,
        "valorEntrada": 10000.00,
        "saldoDevedor": 90000.00,
    }


@pytest.fixture
def sample_parcela_data() -> dict:
    """Sample installment data for testing."""
    return {
        "codigoParcela": 1,
        "codigoContrato": 1234,
        "numeroParcela": 1,
        "dataVencimento": "2024-02-01",
        "dataPagamento": "2024-02-01",
        "valorParcela": 8333.33,
        "valorPago": 8333.33,
        "juros": 0.00,
        "multa": 0.00,
        "desconto": 0.00,
        "status": "pago",
        "tipo": "normal",
    }
