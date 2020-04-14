"""empty message

Revision ID: b78a734006fc
Revises: 5608765dc3c8
Create Date: 2020-03-18 05:31:42.986270

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = 'b78a734006fc'
down_revision = '5608765dc3c8'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('users', 'token')
    op.alter_column('users', 'crypt', new_column_name='token',
                    existing_type=sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType()
                    )
    # ### end Alembic commands ###


def downgrade():
    op.alter_column('users', 'token', new_column_name='crypt',
                    existing_type=sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType()
                    )
    op.add_column('users', sa.Column('token', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=True))
    # ### end Alembic commands ###
