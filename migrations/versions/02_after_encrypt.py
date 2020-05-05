"""
Make sure the dev admin function 'encrypt()' has been run to copy (and encrypt) values from token to crypt columns.
User Model should have the following fields:

token = db.Column(db.String(255),               index=False, unique=False, nullable=True)
crypt = db.Column(EncryptedType(db.String(255), SECRET_KEY, AesEngine, 'pkcs5'))  # encrypt

After running this migration, the User Model should have the following replace the above 2 lines:

token = db.Column(EncryptedType(db.String(255), SECRET_KEY, AesEngine, 'pkcs5'))  # encrypt

Then the admin can call to subscribe to pages for all users that gave us their instagram id.

Revision ID: 02_after_encrypt
Revises: 01_initial
Create Date: 2020-04-20 16:04:55.000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '02_after_encrypt'
down_revision = '01_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('users', 'token')
    op.alter_column('users', 'crypt', new_column_name='token',
                    existing_type=sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType()
                    )
    op.alter_column('posts', 'comments_count',  existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'like_count',      existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'impressions',     existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'reach',           existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'engagement',      existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'saved',           existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'video_views',     existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'exits',           existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'replies',         existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'taps_forward',    existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('posts', 'taps_back',       existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('onlinefollowers', 'value', existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)
    op.alter_column('insights', 'value',        existing_type=mysql.INTEGER(11), existing_nullable=True, nullable=False, default=0)


def downgrade():
    """ If downgrading, after running this downgrade you will need to copy values from crypt to token. User model needs:

        token = db.Column(db.String(255),               index=False, unique=False, nullable=True)
        crypt = db.Column(EncryptedType(db.String(255), SECRET_KEY, AesEngine, 'pkcs5'))  # encrypt
    """
    op.alter_column('posts', 'comments_count',  existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'like_count',      existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'impressions',     existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'reach',           existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'engagement',      existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'saved',           existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'video_views',     existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'exits',           existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'replies',         existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'taps_forward',    existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('posts', 'taps_back',       existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('onlinefollowers', 'value', existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('insights', 'value',        existing_type=mysql.INTEGER(11), existing_nullable=False, nullable=True, existing_default=0, default=None)
    op.alter_column('users', 'token', new_column_name='crypt',
                    existing_type=sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType()
                    )
    op.add_column('users', sa.Column('token', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=True))
