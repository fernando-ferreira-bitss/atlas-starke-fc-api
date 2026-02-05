"""Create default admin user.

Creates initial admin user for new installations:
- Email: admin@starke.com
- Password: admin123

Revision ID: create_default_admin_user
Revises: remove_patrimony_tables
Create Date: 2026-02-05

"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'create_default_admin_user'
down_revision = 'remove_patrimony_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create default admin user if not exists."""
    # Hash for 'admin123' using bcrypt
    password_hash = "$2b$12$6WF7ct7I7sTEKNrS.4sm9uk/gV6x84vUHIRiJztAlbd4YyUr5f/EW"

    # Insert admin user only if email doesn't already exist
    op.execute(f"""
        INSERT INTO users (email, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at)
        SELECT 'admin@starke.com', '{password_hash}', 'Administrador', 'admin', true, true, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@starke.com')
    """)


def downgrade():
    """Remove default admin user."""
    op.execute("DELETE FROM users WHERE email = 'admin@starke.com'")
