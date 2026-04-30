"""add account_id to profiles and migrate from user_id

Revision ID: 20260323_add_account_id_to_profiles
Revises: 
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260323_add_account_id_to_profiles'
down_revision = None  # Se ajustará automáticamente al hacer merge de heads
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Añadir la columna account_id como nullable primero (para poder rellenarla)
    op.add_column('profiles',
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # 2. Copiar el valor de user_id a account_id si user_id existe y es UUID válido
    #    (user_id era el campo antiguo que apuntaba a accounts.id)
    op.execute("""
        UPDATE profiles 
        SET account_id = user_id::uuid
        WHERE user_id IS NOT NULL
          AND user_id::text ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    """)
    
    # 3. Si queda algún perfil sin account_id, intentamos vincularlo al primer admin disponible
    #    (para no dejar huérfanos que rompan el NOT NULL constraint)
    op.execute("""
        UPDATE profiles 
        SET account_id = (SELECT id FROM accounts LIMIT 1)
        WHERE account_id IS NULL
    """)
    
    # 4. Añadir la FK y el constraint NOT NULL
    op.create_foreign_key(
        'fk_profiles_account_id',
        'profiles', 'accounts',
        ['account_id'], ['id'],
        ondelete='CASCADE'
    )
    op.alter_column('profiles', 'account_id', nullable=False)
    
    # 5. Añadir el constraint UNIQUE (una cuenta -> un perfil)
    op.create_unique_constraint('uq_profiles_account_id', 'profiles', ['account_id'])


def downgrade() -> None:
    op.drop_constraint('uq_profiles_account_id', 'profiles', type_='unique')
    op.drop_constraint('fk_profiles_account_id', 'profiles', type_='foreignkey')
    op.drop_column('profiles', 'account_id')
