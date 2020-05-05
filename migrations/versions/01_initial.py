"""
After running, make sure the dev admin function 'encrypt()` has been run.
This should also call the fix_defaults() dev admin function.

Revision ID: 01_initial
Revises:
Create Date: 2020-04-20 13:19:41.151481

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = '01_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('post_campaigns',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('post_id', sa.Integer(), nullable=True),
                    sa.Column('campaign_id', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('processed_campaigns',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('post_id', sa.Integer(), nullable=True),
                    sa.Column('campaign_id', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.add_column('posts', sa.Column('saved_media', sa.Text(), nullable=True))
    op.add_column('posts', sa.Column('capture_name', sa.String(length=191), nullable=True))
    op.alter_column('posts', 'user_id', existing_type=mysql.INTEGER(display_width=11), nullable=True)
    op.drop_constraint('posts_ibfk_1', 'posts', type_='foreignkey')
    op.drop_constraint('posts_ibfk_2', 'posts', type_='foreignkey')
    op.create_foreign_key('posts_ibfk_1', 'posts', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.drop_column('posts', 'campaign_id')
    op.drop_column('posts', 'processed')
    op.add_column('users', sa.Column('crypt', sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(), nullable=True))
    op.add_column('users', sa.Column('story_subscribed', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('page_id', mysql.BIGINT(unsigned=True), nullable=True))
    op.add_column('users', sa.Column('page_token', sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(), nullable=True))
    op.create_unique_constraint(None, 'users', ['page_id'])


def downgrade():
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'page_token')
    op.drop_column('users', 'story_subscribed')
    op.drop_column('users', 'page_id')
    op.drop_column('users', 'crypt')
    op.add_column('posts', sa.Column('processed', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True))
    op.add_column('posts', sa.Column('campaign_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.drop_constraint('posts_ibfk_1', 'posts', type_='foreignkey')
    op.alter_column('posts', 'user_id', existing_type=mysql.INTEGER(display_width=11), nullable=False)
    op.create_foreign_key('posts_ibfk_2', 'posts', 'campaigns', ['campaign_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('posts_ibfk_1', 'posts', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_column('posts', 'capture_name')
    op.drop_column('posts', 'saved_media')
    op.drop_table('processed_campaigns')
    op.drop_table('post_campaigns')
