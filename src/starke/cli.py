"""CLI application entry point."""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from starke.core.config import get_settings
from starke.core.logging import configure_logging, get_logger
from starke.core.orchestrator import Orchestrator
from starke.infrastructure.database.base import init_db, get_session
from starke.infrastructure.email.email_service import EmailService
from starke.infrastructure.external_apis.mega_api_client import MegaAPIClient
from starke.infrastructure.external_apis.uau_api_client import UAUAPIClient
from starke.domain.services.mega_sync_service import MegaSyncService
from starke.domain.services.uau_sync_service import UAUSyncService

# Load environment variables from .env file
dotenv_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path)

# Configure logging on module import
configure_logging()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def app() -> None:
    """Starke - Sistema de Relatórios de Fluxo de Caixa."""
    pass


@app.command()
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Data de referência (formato: YYYY-MM-DD). Padrão: ontem (T-1)",
)
@click.option(
    "--empreendimento-ids",
    help="IDs de empreendimentos separados por vírgula (ex: 1,2,3). Se omitido, processa todos.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Executa o processamento mas não envia emails",
)
@click.option(
    "--skip-ingestion",
    is_flag=True,
    help="Pula a etapa de ingestão (usa dados já existentes no banco)",
)
def run(
    date: Optional[datetime],
    empreendimento_ids: Optional[str],
    dry_run: bool,
    skip_ingestion: bool,
) -> None:
    """Executa o processamento completo do relatório de fluxo de caixa."""
    # Determine reference date (default to yesterday)
    if date:
        ref_date = date.date()
    else:
        ref_date = (datetime.now() - timedelta(days=1)).date()

    # Parse empreendimento IDs
    emp_ids = None
    if empreendimento_ids:
        try:
            emp_ids = [int(x.strip()) for x in empreendimento_ids.split(",")]
        except ValueError:
            click.echo("❌ Erro: IDs de empreendimento inválidos", err=True)
            raise click.Abort()

    click.echo(f"🚀 Iniciando processamento para {ref_date.isoformat()}")
    if dry_run:
        click.echo("   [DRY RUN MODE - Emails não serão enviados]")

    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")

        # Create orchestrator
        orchestrator = Orchestrator()

        # Execute
        result = orchestrator.execute(
            ref_date=ref_date,
            empreendimento_ids=emp_ids,
            dry_run=dry_run,
            skip_ingestion=skip_ingestion,
        )

        # Display results
        click.echo("\n✅ Processamento concluído com sucesso!")
        click.echo(f"\n📊 Resumo:")
        click.echo(f"   • Empreendimentos processados: {result.get('empreendimentos_count', 0)}")
        click.echo(f"   • Contratos coletados: {result.get('total_contracts', 0)}")
        click.echo(f"   • Parcelas processadas: {result.get('total_installments', 0)}")
        click.echo(f"   • Relatórios gerados: {result.get('reports_generated', 0)}")

        if not dry_run:
            click.echo(f"   • Emails enviados: {result.get('emails_sent', 0)}")
            if result.get('emails_failed', 0) > 0:
                click.echo(f"   ⚠️  Emails com falha: {result.get('emails_failed', 0)}")

    except Exception as e:
        logger.error("Execution failed", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro durante execução: {e}", err=True)
        raise click.Abort()


@app.command()
def init() -> None:
    """Inicializa o banco de dados."""
    click.echo("🔧 Inicializando banco de dados...")
    try:
        init_db()
        click.echo("✅ Banco de dados inicializado com sucesso!")
    except Exception as e:
        click.echo(f"❌ Erro ao inicializar banco: {e}", err=True)
        raise click.Abort()


@app.command()
@click.option(
    "--email",
    required=True,
    help="Email para enviar o teste",
)
def test_email(email: str) -> None:
    """Testa a configuração de email enviando um email de teste."""
    click.echo(f"📧 Enviando email de teste para {email}...")

    try:
        email_service = EmailService()
        success = email_service.send_test_email(email)

        if success:
            click.echo("✅ Email de teste enviado com sucesso!")
        else:
            click.echo("❌ Falha ao enviar email de teste", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"❌ Erro: {e}", err=True)
        raise click.Abort()




@app.command()
def test_simple() -> None:
    """
    Executa um teste simples do sistema completo.

    - Usa dados de exemplo (não consulta API)
    - Gera relatório HTML
    - Envia para TEST_EMAIL_RECIPIENT (se TEST_MODE=true)
    """
    from datetime import date, timedelta
    from decimal import Decimal

    from starke.domain.entities.cash_flow import (
        BalanceData,
        CashInCategory,
        CashInData,
        CashOutCategory,
        CashOutData,
        PortfolioStatsData,
    )
    from starke.infrastructure.email.email_service import EmailService
    from starke.presentation.report_builder import ReportBuilder

    settings = get_settings()

    click.echo("🧪 Executando teste simples do sistema...\n")

    # Verificar configurações
    if not settings.test_mode:
        click.echo("⚠️  TEST_MODE não está habilitado no .env")
        click.echo("   Configure: TEST_MODE=true")
        raise click.Abort()

    if not settings.test_email_recipient:
        click.echo("⚠️  TEST_EMAIL_RECIPIENT não configurado no .env")
        click.echo("   Configure: TEST_EMAIL_RECIPIENT=seu@email.com")
        raise click.Abort()

    click.echo(f"📧 Email de teste: {settings.test_email_recipient}\n")

    try:
        # Dados de exemplo
        ref_date = date.today() - timedelta(days=1)

        click.echo("📊 Criando dados de exemplo...")

        # Entradas de caixa
        cash_in_list = [
            CashInData(
                empreendimento_id=1,
                empreendimento_nome="Empreendimento Teste",
                ref_date=ref_date,
                category=CashInCategory.ATIVOS,
                forecast=Decimal("100000.00"),
                actual=Decimal("95000.00"),
            ),
            CashInData(
                empreendimento_id=1,
                empreendimento_nome="Empreendimento Teste",
                ref_date=ref_date,
                category=CashInCategory.RECUPERACOES,
                forecast=Decimal("5000.00"),
                actual=Decimal("6000.00"),
            ),
        ]

        # Saídas de caixa
        cash_out_list = [
            CashOutData(
                empreendimento_id=1,
                empreendimento_nome="Empreendimento Teste",
                ref_date=ref_date,
                category=CashOutCategory.OPEX,
                budget=Decimal("30000.00"),
                actual=Decimal("28500.00"),
            ),
            CashOutData(
                empreendimento_id=1,
                empreendimento_nome="Empreendimento Teste",
                ref_date=ref_date,
                category=CashOutCategory.FINANCEIRAS,
                budget=Decimal("10000.00"),
                actual=Decimal("10500.00"),
            ),
        ]

        # Saldo
        balance = BalanceData(
            empreendimento_id=1,
            empreendimento_nome="Empreendimento Teste",
            ref_date=ref_date,
            opening=Decimal("50000.00"),
            closing=Decimal("112000.00"),
            total_in=Decimal("101000.00"),
            total_out=Decimal("39000.00"),
        )

        # Estatísticas da carteira
        portfolio_stats = PortfolioStatsData(
            empreendimento_id=1,
            empreendimento_nome="Empreendimento Teste",
            ref_date=ref_date,
            vp=Decimal("5000000.00"),
            ltv=Decimal("75.5"),
            prazo_medio=Decimal("36.0"),
            duration=Decimal("28.5"),
            total_contracts=150,
            active_contracts=142,
        )

        click.echo("✅ Dados criados\n")

        # Gerar relatório HTML (versão email com barras HTML/CSS)
        click.echo("📄 Gerando relatório HTML para email...")
        builder = ReportBuilder()
        html = builder.build_report(
            empreendimento_id=1,
            empreendimento_nome="Empreendimento Teste",
            ref_date=ref_date,
            cash_in_list=cash_in_list,
            cash_out_list=cash_out_list,
            for_email=True,  # Use email-compatible template
            balance=balance,
            portfolio_stats=portfolio_stats,
        )
        click.echo(f"✅ Relatório gerado ({len(html)} caracteres)\n")

        # Enviar email
        click.echo(f"📧 Enviando email para {settings.test_email_recipient}...")
        email_service = EmailService()

        recipients = [{
            "name": "Teste",
            "email": settings.test_email_recipient
        }]

        result = email_service.send_html_email(
            recipients=recipients,
            subject=f"Teste - Fluxo de Caixa - {ref_date.strftime('%d/%m/%Y')}",
            html_body=html,
        )

        if result["sent"] > 0:
            click.echo("✅ Email enviado com sucesso!\n")
            click.echo("📬 Verifique sua caixa de entrada:")
            click.echo(f"   {settings.test_email_recipient}\n")
        else:
            click.echo("❌ Falha ao enviar email", err=True)
            if result["failures"]:
                for failure in result["failures"]:
                    click.echo(f"   Erro: {failure['error']}", err=True)
            raise click.Abort()

        click.echo("🎉 Teste concluído com sucesso!")

    except Exception as e:
        click.echo(f"\n❌ Erro durante teste: {e}", err=True)
        import traceback
        traceback.print_exc()
        raise click.Abort()


@app.command()
def list_empreendimentos() -> None:
    """Lista todos os empreendimentos da API Mega."""
    click.echo("📋 Listando empreendimentos da API Mega...\n")

    try:
        from starke.infrastructure.external_apis.mega_client import MegaAPIClient

        with MegaAPIClient() as client:
            empreendimentos = client.get_empreendimentos()

            if not empreendimentos:
                click.echo("⚠️  Nenhum empreendimento encontrado")
                return

            click.echo(f"✅ Encontrados {len(empreendimentos)} empreendimentos:\n")

            for emp in empreendimentos:
                # Adaptar campos conforme resposta real da API
                emp_id = emp.get("codigo") or emp.get("est_in_codigo") or emp.get("id")
                nome = emp.get("nome") or emp.get("est_st_nome") or "N/A"
                status = emp.get("est_ch_status") or "N/A"

                click.echo(f"  • ID: {emp_id} | Nome: {nome} | Status: {status}")

    except Exception as e:
        logger.error("Failed to list empreendimentos", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro ao listar empreendimentos: {e}", err=True)
        raise click.Abort()


@app.command()
def config() -> None:
    """Mostra a configuração atual."""
    settings = get_settings()

    click.echo("⚙️  Configuração Atual:\n")
    click.echo(f"Environment:    {settings.environment}")
    click.echo(f"Debug:          {settings.debug}")
    click.echo(f"Log Level:      {settings.log_level}")
    click.echo(f"\nDatabase:       {settings.database_url}")
    click.echo(f"\nAPI Base URL:   {settings.mega_api_url}")
    click.echo(f"API Username:   {settings.mega_api_username}")
    click.echo(f"\nEmail Backend:  {settings.email_backend}")
    click.echo(f"Email From:     {settings.email_from_name} <{settings.email_from_address}>")

    if settings.email_backend == "smtp":
        click.echo(f"SMTP Host:      {settings.smtp_host}:{settings.smtp_port}")

    click.echo(f"\nTimezone:       {settings.report_timezone}")
    click.echo(f"Execution Time: {settings.execution_time}")

    click.echo(f"\n🧪 Test Mode:    {settings.test_mode}")
    if settings.test_mode:
        click.echo(f"Test Email:     {settings.test_email_recipient}")


@app.command()
@click.option("--email", required=True, prompt=True, help="Email do usuário")
@click.option(
    "--password",
    required=True,
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Senha do usuário",
)
@click.option("--superuser", is_flag=True, help="Criar como superusuário (admin)")
def create_user(email: str, password: str, superuser: bool) -> None:
    """Cria um novo usuário no sistema."""
    from starke.domain.services.auth_service import AuthService
    from starke.infrastructure.database.base import SessionLocal

    click.echo(f"👤 Criando usuário: {email}")

    try:
        with SessionLocal() as db:
            auth_service = AuthService(db)
            user = auth_service.create_user(
                email=email, password=password, is_superuser=superuser
            )
            click.echo(f"✅ Usuário criado com sucesso! ID: {user.id}")
            if superuser:
                click.echo("   🔑 Privilégios de administrador concedidos")

    except ValueError as e:
        click.echo(f"❌ Erro: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        raise click.Abort()


@app.command()
def list_users() -> None:
    """Lista todos os usuários do sistema."""
    from starke.infrastructure.database.base import SessionLocal
    from starke.infrastructure.database.models import User

    click.echo("👥 Usuários cadastrados:\n")

    try:
        with SessionLocal() as db:
            users = db.query(User).order_by(User.email).all()

            if not users:
                click.echo("   Nenhum usuário encontrado")
                return

            for user in users:
                status = "✅" if user.is_active else "❌"
                admin = " 🔑" if user.is_superuser else ""
                click.echo(f"   {status} [{user.id}] {user.email}{admin}")

            click.echo(f"\nTotal: {len(users)} usuários")

    except Exception as e:
        click.echo(f"❌ Erro: {e}", err=True)
        raise click.Abort()


@app.command()
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Data inicial do período (formato: YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Data final do período (formato: YYYY-MM-DD). Padrão: ontem",
)
@click.option(
    "--empreendimento-ids",
    help="IDs de empreendimentos separados por vírgula (ex: 1,2,3). Se omitido, processa todos.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Executa o processamento mas não envia emails",
)
@click.option(
    "--max-months",
    type=int,
    default=24,
    help="Número máximo de meses permitidos (padrão: 24). Use --force para ignorar.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Força processamento mesmo com muitos meses (ignora limite)",
)
@click.option(
    "--skip-recent-hours",
    type=int,
    default=0,
    help="Pula empreendimentos sincronizados nas últimas X horas (checkpoint). 0 = processa todos.",
)
def backfill(
    start_date: datetime,
    end_date: Optional[datetime],
    empreendimento_ids: Optional[str],
    dry_run: bool,
    max_months: int,
    force: bool,
    skip_recent_hours: int,
) -> None:
    """
    Processa múltiplos meses (backfill de histórico).

    Por padrão, limita a 24 meses. Use --max-months ou --force para mais.

    Exemplos:
      # Processar todo o ano de 2025
      python -m starke.cli backfill --start-date=2025-01-01 --end-date=2025-12-31

      # Processar primeiro semestre de 2025
      python -m starke.cli backfill --start-date=2025-01-01 --end-date=2025-06-30

      # Processar de janeiro até hoje
      python -m starke.cli backfill --start-date=2025-01-01

      # Processar apenas um empreendimento
      python -m starke.cli backfill --start-date=2025-01-01 --empreendimento-ids=1472

      # Processar mais de 24 meses (permite até 36)
      python -m starke.cli backfill --start-date=2023-01-01 --max-months=36

      # Forçar processamento sem confirmação
      python -m starke.cli backfill --start-date=2020-01-01 --force

      # Continuar de onde parou (pula empreendimentos sincronizados nas últimas 6h)
      python -m starke.cli backfill --start-date=2025-01-01 --skip-recent-hours=6
    """
    # Determine end date (default to yesterday)
    if end_date:
        final_date = end_date.date()
    else:
        final_date = (datetime.now() - timedelta(days=1)).date()

    initial_date = start_date.date()

    # Validate dates
    if initial_date > final_date:
        click.echo("❌ Erro: Data inicial não pode ser maior que data final", err=True)
        raise click.Abort()

    # Parse empreendimento IDs
    emp_ids = None
    if empreendimento_ids:
        try:
            emp_ids = [int(x.strip()) for x in empreendimento_ids.split(",")]
        except ValueError:
            click.echo("❌ Erro: IDs de empreendimento inválidos", err=True)
            raise click.Abort()

    click.echo(f"🚀 Iniciando backfill de {initial_date.isoformat()} até {final_date.isoformat()}")
    if dry_run:
        click.echo("   [DRY RUN MODE - Emails não serão enviados]")
    if skip_recent_hours > 0:
        click.echo(f"   [CHECKPOINT MODE - Pulando empreendimentos sincronizados nas últimas {skip_recent_hours}h]")

    # Calculate months to process
    months_to_process = []
    current = initial_date.replace(day=1)

    while current <= final_date:
        # Calculate last day of month or final_date (whichever is earlier)
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)

        last_day_of_month = (next_month - timedelta(days=1))
        ref_date = min(last_day_of_month, final_date)

        months_to_process.append({
            "ref_month": f"{current.year}-{current.month:02d}",
            "ref_date": ref_date,
        })

        current = next_month

    click.echo(f"\n📅 Serão processados {len(months_to_process)} meses:")
    for month_info in months_to_process:
        click.echo(f"   • {month_info['ref_month']} (ref_date: {month_info['ref_date']})")

    click.echo()

    # Validate max months limit
    if not force and len(months_to_process) > max_months:
        click.echo(f"❌ Erro: Tentando processar {len(months_to_process)} meses, "
                  f"mas o limite é {max_months}", err=True)
        click.echo(f"   Use --max-months={len(months_to_process)} ou --force para ignorar o limite", err=True)
        raise click.Abort()

    # Warn if many months
    if len(months_to_process) > 12:
        click.echo(f"⚠️  Atenção: Você está prestes a processar {len(months_to_process)} meses!")
        click.echo("   Isso pode demorar bastante e gerar muitas chamadas à API.")
        if not force and not click.confirm("   Deseja continuar?", default=False):
            click.echo("❌ Operação cancelada pelo usuário")
            raise click.Abort()

    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")

        # Use optimized MegaSyncService workflow
        click.echo("🔄 Usando workflow otimizado (MegaSyncService)...")
        click.echo("   • Busca contratos apenas 1 vez")
        click.echo("   • Salva contratos durante o processamento")
        click.echo("   • Processa apenas empreendimentos ativos\n")

        with get_session() as db:
            with MegaAPIClient() as api_client:
                click.echo("✅ Conectado ao banco de dados e API Mega")

                with MegaSyncService(db, api_client) as sync_service:
                    # Process entire date range in one optimized workflow
                    click.echo(f"🚀 Iniciando sincronização completa...")

                    stats = sync_service.sync_all(
                        start_date=initial_date,
                        end_date=final_date,
                        development_ids=emp_ids,
                        sync_developments=True,
                        sync_contracts=True,
                        sync_financial=True,
                        skip_recent_hours=skip_recent_hours,
                    )

                    click.echo("\n✅ Sincronização concluída!")

        # Display final summary
        click.echo("\n" + "="*80)
        click.echo("✅ Backfill concluído com sucesso!")
        click.echo("="*80)
        click.echo(f"\n📊 Resumo Total:")
        click.echo(f"   • Período: {initial_date} a {final_date}")
        click.echo(f"   • Empreendimentos sincronizados: {stats.get('developments_synced', 0)}")
        if stats.get('developments_skipped', 0) > 0:
            click.echo(f"   • Empreendimentos pulados (checkpoint): {stats.get('developments_skipped', 0)}")
        click.echo(f"   • Contratos salvos no banco: {stats.get('contracts_synced', 0)}")
        click.echo(f"   • Registros CashIn: {stats.get('cash_in_records', 0)}")
        click.echo(f"   • Registros CashOut: {stats.get('cash_out_records', 0)}")
        if stats.get('errors'):
            click.echo(f"   • Erros encontrados: {len(stats.get('errors'))}")
        click.echo(f"\n💡 Dica: Use o dashboard web para visualizar os dados históricos")

    except Exception as e:
        logger.error("Backfill failed", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro durante backfill: {e}", err=True)
        raise click.Abort()


@app.command()
@click.option(
    "--empreendimento-ids",
    help="IDs de empreendimentos separados por vírgula (ex: 1,2,3). Se omitido, sincroniza todos.",
)
def sync_contracts(empreendimento_ids: Optional[str]) -> None:
    """
    Sincroniza empreendimentos e contratos da API Mega para o banco de dados local.

    Fluxo de sincronização:
    1. Sincroniza TODOS os empreendimentos com is_active = False
    2. Sincroniza os contratos para cada empreendimento
    3. Atualiza is_active = True para empreendimentos com pelo menos 1 contrato status='Ativo'

    Os contratos são usados para:
    - Determinar quais empreendimentos estão ativos (Development.is_active)
    - Filtrar despesas por contrato (usando Agente.Codigo)

    Exemplos:
      # Sincronizar todos os empreendimentos e contratos
      python -m starke.cli sync-contracts

      # Sincronizar contratos de empreendimentos específicos
      python -m starke.cli sync-contracts --empreendimento-ids=1472,1500
    """
    from starke.domain.services.contract_service import ContractService
    from starke.domain.services.development_service import DevelopmentService
    from starke.infrastructure.database.base import SessionLocal
    from starke.infrastructure.external_apis.mega_client import MegaAPIClient

    click.echo("📋 Sincronizando dados da API Mega...\n")

    try:
        # STEP 1: Sync all empreendimentos first (sets is_active = False)
        click.echo("🏢 PASSO 1: Sincronizando empreendimentos...\n")
        with SessionLocal() as db:
            dev_service = DevelopmentService(db)
            dev_summary = dev_service.sync_from_mega_api()

            click.echo(f"   • Total processados: {dev_summary['total']}")
            click.echo(f"   • Novos criados: {dev_summary['created']}")
            click.echo(f"   • Atualizados: {dev_summary['updated']}")
            if dev_summary['errors']:
                click.echo(f"   ⚠️  Erros: {len(dev_summary['errors'])}")

        # Parse empreendimento IDs for contract sync
        emp_ids = None
        if empreendimento_ids:
            try:
                emp_ids = [int(x.strip()) for x in empreendimento_ids.split(",")]
                click.echo(f"\n🎯 PASSO 2: Sincronizando contratos de {len(emp_ids)} empreendimentos específicos")
            except ValueError:
                click.echo("❌ Erro: IDs de empreendimento inválidos", err=True)
                raise click.Abort()
        else:
            # Fetch all empreendimentos from API
            with MegaAPIClient() as client:
                empreendimentos = client.get_empreendimentos()

                # Filtrar empreendimentos que contêm "teste" ou "SIMULAÇÃO" no nome
                empreendimentos_filtrados = []
                ignorados = 0
                for emp in empreendimentos:
                    nome = (emp.get("nome") or emp.get("est_st_nome") or emp.get("descricao") or "").upper()

                    # Ignorar se contém "TESTE" ou é "SIMULAÇÃO"
                    if "TESTE" in nome or nome == "SIMULAÇÃO":
                        ignorados += 1
                        continue

                    empreendimentos_filtrados.append(emp)

                emp_ids = [
                    int(emp.get("codigo") or emp.get("est_in_codigo"))
                    for emp in empreendimentos_filtrados
                    if emp.get("codigo") or emp.get("est_in_codigo")
                ]

                click.echo(f"\n🎯 PASSO 2: Sincronizando contratos de {len(emp_ids)} empreendimentos")
                if ignorados > 0:
                    click.echo(f"   ℹ️  Ignorados {ignorados} empreendimentos (teste/simulação)")

        click.echo(f"\n⏳ Buscando contratos e atualizando status dos empreendimentos...\n")

        # Sync contracts
        with SessionLocal() as db:
            with MegaAPIClient() as client:
                service = ContractService(db, client)
                stats = service.fetch_and_save_contracts(emp_ids)

        # Display results
        click.echo("\n✅ Sincronização concluída!\n")
        click.echo("📊 Estatísticas:")
        click.echo(f"   • Empreendimentos processados: {stats['developments_processed']}/{stats['total_developments']}")
        click.echo(f"   • Contratos encontrados: {stats['contracts_fetched']}")
        click.echo(f"   • Novos contratos salvos: {stats['contracts_saved']}")
        click.echo(f"   • Contratos anteriores excluídos: {stats['contracts_deleted']}")

        if stats['errors'] > 0:
            click.echo(f"   ⚠️  Erros: {stats['errors']}")

        # Show active developments and contract summary
        with SessionLocal() as db:
            with MegaAPIClient() as client:
                dev_service = DevelopmentService(db)
                active_developments = dev_service.get_all_developments(active_only=True)

                click.echo(f"\n✨ Empreendimentos ativos (com pelo menos 1 contrato status='Ativo'): {len(active_developments)}")

                if active_developments and len(active_developments) <= 20:
                    click.echo("\n   IDs:")
                    for dev in sorted(active_developments, key=lambda d: d.id):
                        click.echo(f"   • {dev.id} - {dev.name}")

                # Show contract status summary
                service = ContractService(db, client)
                status_counts = service.get_contract_count_by_status()
                click.echo(f"\n📈 Contratos por status:")
                for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                    click.echo(f"   • {status}: {count}")

    except Exception as e:
        logger.error("Failed to sync contracts", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro ao sincronizar contratos: {e}", err=True)
        raise click.Abort()


@app.command()
@click.option(
    "--start-date",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Data inicial para sincronização (formato: YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Data final para sincronização (formato: YYYY-MM-DD)",
)
@click.option(
    "--filial-ids",
    help="IDs de filiais separados por vírgula (ex: 10301,10302). Se omitido, sincroniza todas.",
)
@click.option(
    "--aggregate",
    is_flag=True,
    help="Após sincronizar, agregar faturas em CashOut",
)
def sync_faturas(
    start_date: datetime,
    end_date: datetime,
    filial_ids: Optional[str],
    aggregate: bool,
) -> None:
    """
    Sincroniza faturas a pagar da API Mega para o banco de dados local.

    Este comando:
    1. Busca faturas do endpoint /api/FinanceiroMovimentacao/FaturaPagar/Saldo
    2. Processa cada fatura determinando data_baixa baseado em:
       - Se fatura existe no DB com saldo > 0 e agora saldo = 0 → data_baixa = hoje
       - Se fatura não existe no DB e saldo = 0 → data_baixa = data_vencimento
       - Caso contrário → data_baixa = NULL
    3. Salva/atualiza faturas na tabela faturas_pagar
    4. Opcionalmente agrega faturas em CashOut (--aggregate)

    Exemplos:
      # Sincronizar faturas de julho a novembro/2025
      python -m starke.cli sync-faturas --start-date=2025-07-01 --end-date=2025-11-30

      # Sincronizar e agregar em CashOut
      python -m starke.cli sync-faturas --start-date=2025-07-01 --end-date=2025-11-30 --aggregate

      # Sincronizar apenas filiais específicas
      python -m starke.cli sync-faturas --start-date=2025-07-01 --end-date=2025-11-30 --filial-ids=10301,10302
    """
    from starke.infrastructure.database.base import SessionLocal

    click.echo("💰 Sincronizando faturas a pagar da API Mega...\n")

    # Parse filial IDs
    filial_id_list = None
    if filial_ids:
        try:
            filial_id_list = [int(x.strip()) for x in filial_ids.split(",")]
            click.echo(f"🎯 Filiais filtradas: {filial_id_list}")
        except ValueError:
            click.echo("❌ Erro: IDs de filial inválidos", err=True)
            raise click.Abort()

    start = start_date.date()
    end = end_date.date()

    click.echo(f"📅 Período: {start} a {end}\n")

    try:
        # Initialize database and sync service
        init_db()

        with SessionLocal() as db:
            with MegaAPIClient() as api_client:
                sync_service = MegaSyncService(db, api_client)

                # Step 1: Sync faturas
                click.echo("⏳ PASSO 1: Sincronizando faturas...\n")
                count = sync_service.sync_faturas_pagar(
                    start_date=start,
                    end_date=end,
                    filial_ids=filial_id_list
                )

                click.echo(f"\n✅ {count} faturas sincronizadas com sucesso!")

                # Step 2: Aggregate if requested
                if aggregate:
                    click.echo("\n⏳ PASSO 2: Agregando faturas em CashOut...\n")
                    agg_count = sync_service.aggregate_cash_out_from_faturas(
                        ref_month=None,  # Aggregate all months
                        filial_ids=filial_id_list
                    )
                    click.echo(f"\n✅ {agg_count} registros CashOut criados/atualizados!")

        click.echo("\n" + "="*80)
        click.echo("✅ Sincronização de faturas concluída com sucesso!")
        click.echo("="*80)

    except Exception as e:
        logger.error("Failed to sync faturas", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro ao sincronizar faturas: {e}", err=True)
        raise click.Abort()


@app.command()
@click.option("--host", default="0.0.0.0", help="Host para o servidor API")
@click.option("--port", default=8000, help="Porta para o servidor API")
@click.option("--reload", is_flag=True, help="Recarregar automaticamente (desenvolvimento)")
def serve(host: str, port: int, reload: bool) -> None:
    """Inicia o servidor API FastAPI."""
    import uvicorn

    click.echo(f"🚀 Iniciando servidor API em http://{host}:{port}")
    click.echo(f"📖 Documentação disponível em: http://{host}:{port}/docs")

    try:
        uvicorn.run(
            "starke.api.main:app",
            host=host,
            port=port,
            reload=reload,
        )
    except Exception as e:
        click.echo(f"❌ Erro ao iniciar servidor: {e}", err=True)
        raise click.Abort()


# ==============================================
# UAU API Commands
# ==============================================

@app.command()
def uau_list_empresas() -> None:
    """Lista todas as empresas da API UAU."""
    click.echo("📋 Listando empresas da API UAU...\n")

    settings = get_settings()

    if not settings.uau_api_url or not settings.uau_integration_token:
        click.echo("❌ Erro: Configuração UAU não encontrada no .env", err=True)
        click.echo("   Configure: UAU_API_URL, UAU_INTEGRATION_TOKEN, UAU_USERNAME, UAU_PASSWORD", err=True)
        raise click.Abort()

    try:
        with UAUAPIClient() as client:
            empresas = client.get_empresas()

            if not empresas:
                click.echo("⚠️  Nenhuma empresa encontrada")
                return

            click.echo(f"✅ Encontradas {len(empresas)} empresas:\n")

            for emp in empresas:
                emp_id = emp.get("Codigo_emp") or emp.get("codigo") or "N/A"
                nome = emp.get("Desc_emp") or emp.get("descricao") or "N/A"
                cgc = emp.get("CGC_emp") or ""

                click.echo(f"  • ID: {emp_id} | Nome: {nome}")
                if cgc:
                    click.echo(f"    CNPJ: {cgc}")

    except Exception as e:
        logger.error("Failed to list UAU empresas", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro ao listar empresas UAU: {e}", err=True)
        raise click.Abort()


@app.command()
def uau_config() -> None:
    """Mostra a configuração atual da API UAU."""
    settings = get_settings()

    click.echo("⚙️  Configuração UAU:\n")
    click.echo(f"UAU API URL:    {settings.uau_api_url or '(não configurado)'}")
    click.echo(f"UAU Username:   {settings.uau_username or '(não configurado)'}")
    click.echo(f"UAU Token:      {'***' if settings.uau_integration_token else '(não configurado)'}")
    click.echo(f"UAU Timeout:    {settings.uau_timeout}s")
    click.echo(f"UAU Max Retries: {settings.uau_max_retries}")

    # Test connection
    if settings.uau_api_url and settings.uau_integration_token:
        click.echo("\n🔌 Testando conexão...")
        try:
            with UAUAPIClient() as client:
                # Authenticate
                click.echo("✅ Autenticação bem-sucedida!")
        except Exception as e:
            click.echo(f"❌ Erro na conexão: {e}", err=True)


@app.command()
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Data inicial (formato: YYYY-MM-DD). Padrão: 12 meses atrás",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Data final (formato: YYYY-MM-DD). Padrão: hoje",
)
@click.option(
    "--empresa-ids",
    help="IDs de empresas separados por vírgula (ex: 93,94). Se omitido, sincroniza todas.",
)
@click.option(
    "--only-empresas",
    is_flag=True,
    help="Sincroniza apenas empresas (sem dados financeiros)",
)
@click.option(
    "--only-cash-out",
    is_flag=True,
    help="Sincroniza apenas CashOut (desembolsos)",
)
@click.option(
    "--only-cash-in",
    is_flag=True,
    help="Sincroniza apenas CashIn (parcelas)",
)
def uau_sync(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    empresa_ids: Optional[str],
    only_empresas: bool,
    only_cash_out: bool,
    only_cash_in: bool,
) -> None:
    """
    Sincroniza dados da API UAU para o banco de dados local.

    Este comando:
    1. Sincroniza empresas como Developments (empreendimentos)
    2. Sincroniza CashOut (desembolsos/planejamento)
    3. Sincroniza CashIn (parcelas a receber/recebidas)
    4. Calcula PortfolioStats e Delinquency

    Exemplos:
      # Sincronizar tudo dos últimos 12 meses
      python -m starke.cli uau-sync

      # Sincronizar período específico
      python -m starke.cli uau-sync --start-date=2025-01-01 --end-date=2025-12-31

      # Sincronizar apenas empresas específicas
      python -m starke.cli uau-sync --empresa-ids=93,94

      # Sincronizar apenas empresas (sem dados financeiros)
      python -m starke.cli uau-sync --only-empresas
    """
    from datetime import date as date_type

    settings = get_settings()

    if not settings.uau_api_url or not settings.uau_integration_token:
        click.echo("❌ Erro: Configuração UAU não encontrada no .env", err=True)
        click.echo("   Configure: UAU_API_URL, UAU_INTEGRATION_TOKEN, UAU_USERNAME, UAU_PASSWORD", err=True)
        raise click.Abort()

    # Parse dates
    if end_date:
        final_date = end_date.date()
    else:
        final_date = date_type.today()

    if start_date:
        initial_date = start_date.date()
    else:
        # Default: 12 months ago
        initial_date = date_type(final_date.year - 1, final_date.month, 1)

    # Parse empresa IDs
    emp_ids = None
    if empresa_ids:
        try:
            emp_ids = [int(x.strip()) for x in empresa_ids.split(",")]
        except ValueError:
            click.echo("❌ Erro: IDs de empresa inválidos", err=True)
            raise click.Abort()

    click.echo(f"🚀 Iniciando sincronização UAU")
    click.echo(f"   Período: {initial_date} a {final_date}")
    if emp_ids:
        click.echo(f"   Empresas: {emp_ids}")

    try:
        # Initialize database
        init_db()

        with get_session() as db:
            with UAUAPIClient() as api_client:
                click.echo("\n✅ Conectado ao banco de dados e API UAU")

                sync_service = UAUSyncService(db, api_client)

                if only_empresas:
                    # Sync only empresas
                    click.echo("\n🏢 Sincronizando empresas...")
                    count = sync_service.sync_empresas()
                    click.echo(f"\n✅ {count} empresas sincronizadas!")

                elif only_cash_out:
                    # Sync only CashOut
                    click.echo("\n💸 Sincronizando CashOut (desembolsos)...")
                    # First sync empresas to have them in DB
                    sync_service.sync_empresas()

                    from starke.infrastructure.database.models import Development
                    query = db.query(Development).filter(Development.origem == "uau")
                    if emp_ids:
                        # emp_ids from CLI are external IDs from UAU API
                        query = query.filter(Development.external_id.in_(emp_ids))
                    empresas = query.all()

                    mes_inicial = initial_date.strftime("%m/%Y")
                    mes_final = final_date.strftime("%m/%Y")

                    total = 0
                    for empresa in empresas:
                        # sync_cash_out expects external_id for API calls
                        count = sync_service.sync_cash_out(empresa.external_id, mes_inicial, mes_final)
                        total += count
                        click.echo(f"   • {empresa.name}: {count} registros")

                    click.echo(f"\n✅ {total} registros CashOut sincronizados!")

                elif only_cash_in:
                    # Sync only CashIn
                    click.echo("\n💰 Sincronizando CashIn (parcelas)...")
                    # First sync empresas
                    sync_service.sync_empresas()

                    from starke.infrastructure.database.models import Development
                    query = db.query(Development).filter(Development.origem == "uau")
                    if emp_ids:
                        # emp_ids from CLI are external IDs from UAU API
                        query = query.filter(Development.external_id.in_(emp_ids))
                    empresas = query.all()

                    data_inicio = initial_date.isoformat()
                    data_fim = final_date.isoformat()

                    total = 0
                    for empresa in empresas:
                        # sync_cash_in expects external_id for API calls
                        count = sync_service.sync_cash_in(empresa.external_id, data_inicio, data_fim)
                        total += count
                        click.echo(f"   • {empresa.name}: {count} registros")

                    click.echo(f"\n✅ {total} registros CashIn sincronizados!")

                else:
                    # Full sync
                    click.echo("\n🔄 Executando sincronização completa...")
                    stats = sync_service.sync_all(
                        empresa_ids=emp_ids,
                        start_date=initial_date,
                        end_date=final_date,
                    )

                    click.echo("\n" + "=" * 80)
                    click.echo("✅ Sincronização UAU concluída com sucesso!")
                    click.echo("=" * 80)
                    click.echo(f"\n📊 Resumo:")
                    click.echo(f"   • Empresas sincronizadas: {stats.get('empresas_synced', 0)}")
                    click.echo(f"   • Registros CashOut: {stats.get('cash_out_records', 0)}")
                    click.echo(f"   • Registros CashIn: {stats.get('cash_in_records', 0)}")
                    click.echo(f"   • PortfolioStats: {stats.get('portfolio_stats_records', 0)}")
                    click.echo(f"   • Delinquency: {stats.get('delinquency_records', 0)}")

                    if stats.get('errors'):
                        click.echo(f"\n⚠️  Erros encontrados: {len(stats.get('errors'))}")
                        for err in stats.get('errors')[:5]:
                            click.echo(f"   • {err}")

    except Exception as e:
        logger.error("UAU sync failed", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro durante sincronização UAU: {e}", err=True)
        raise click.Abort()


@app.command()
@click.option(
    "--empresa-id",
    type=int,
    required=True,
    help="ID da empresa UAU",
)
@click.option(
    "--mes-inicial",
    required=True,
    help="Mês inicial (formato: MM/YYYY)",
)
@click.option(
    "--mes-final",
    required=True,
    help="Mês final (formato: MM/YYYY)",
)
def uau_sync_cash_out(empresa_id: int, mes_inicial: str, mes_final: str) -> None:
    """
    Sincroniza CashOut (desembolsos) de uma empresa específica da API UAU.

    Exemplo:
      python -m starke.cli uau-sync-cash-out --empresa-id=93 --mes-inicial=01/2025 --mes-final=12/2025
    """
    settings = get_settings()

    if not settings.uau_api_url:
        click.echo("❌ Erro: Configuração UAU não encontrada no .env", err=True)
        raise click.Abort()

    click.echo(f"💸 Sincronizando CashOut para empresa {empresa_id}")
    click.echo(f"   Período: {mes_inicial} a {mes_final}\n")

    try:
        init_db()

        with get_session() as db:
            with UAUAPIClient() as api_client:
                sync_service = UAUSyncService(db, api_client)

                # Ensure empresa exists
                sync_service.sync_empresas()

                # Sync CashOut
                count = sync_service.sync_cash_out(empresa_id, mes_inicial, mes_final)
                click.echo(f"\n✅ {count} registros CashOut sincronizados!")

    except Exception as e:
        logger.error("UAU CashOut sync failed", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro: {e}", err=True)
        raise click.Abort()


@app.command()
@click.option(
    "--empresa-id",
    type=int,
    required=True,
    help="ID da empresa UAU",
)
@click.option(
    "--data-inicio",
    required=True,
    help="Data inicial (formato: YYYY-MM-DD)",
)
@click.option(
    "--data-fim",
    required=True,
    help="Data final (formato: YYYY-MM-DD)",
)
def uau_sync_cash_in(empresa_id: int, data_inicio: str, data_fim: str) -> None:
    """
    Sincroniza CashIn (parcelas) de uma empresa específica da API UAU.

    Exemplo:
      python -m starke.cli uau-sync-cash-in --empresa-id=93 --data-inicio=2025-01-01 --data-fim=2025-12-31
    """
    settings = get_settings()

    if not settings.uau_api_url:
        click.echo("❌ Erro: Configuração UAU não encontrada no .env", err=True)
        raise click.Abort()

    click.echo(f"💰 Sincronizando CashIn para empresa {empresa_id}")
    click.echo(f"   Período: {data_inicio} a {data_fim}\n")

    try:
        init_db()

        with get_session() as db:
            with UAUAPIClient() as api_client:
                sync_service = UAUSyncService(db, api_client)

                # Ensure empresa exists
                sync_service.sync_empresas()

                # Sync CashIn
                count = sync_service.sync_cash_in(empresa_id, data_inicio, data_fim)
                click.echo(f"\n✅ {count} registros CashIn sincronizados!")

    except Exception as e:
        logger.error("UAU CashIn sync failed", error=str(e), exc_info=True)
        click.echo(f"\n❌ Erro: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    app()
