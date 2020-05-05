"""
Make sure encrypt was called to copy values from token to crypt, but now encrypting the values.
User Model should have the following fields:
# token = db.Column(db.String(255),               index=False, unique=False, nullable=True)
# crypt = db.Column(EncryptedType(db.String(255), SECRET_KEY, AesEngine, 'pkcs5'))  # encrypt
Revision ID: after_encrypt
Revises: 12c30638b715
Create Date: 2020-04-14 00:48:42.602212

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = 'after_encrypt'
down_revision = '12c30638b715'
branch_labels = ('encrypted',)
depends_on = None


def upgrade():
    op.drop_column('users', 'token')
    op.alter_column('users', 'crypt', new_column_name='token',
                    existing_type=sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType()
                    )


def downgrade():
    op.alter_column('users', 'token', new_column_name='crypt',
                    existing_type=sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType()
                    )
    op.add_column('users', sa.Column('token', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=True))
