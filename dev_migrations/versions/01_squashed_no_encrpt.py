"""
Replacing: 12b85a538f29, e8648dab8e18, 5608765dc3c8, 80421895c9c1, dca6e235628f
Skipping: b78a734006fc
The work of the skipped one will be done by 02_after_encrypt_20200413185403
Revision ID: 01_squashed_20200413143615
Revises: e8648dab8e18
Create Date: 2020-04-13 18:47:18.000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '01_squashed_20200413143615'
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
    op.alter_column('posts', 'user_id', existing_type=mysql.INTEGER(display_width=11), nullable=True)
    op.drop_constraint('posts_ibfk_1', 'posts', type_='foreignkey')
    op.drop_constraint('posts_ibfk_2', 'posts', type_='foreignkey')
    op.create_foreign_key(None, 'posts', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.drop_column('posts', 'campaign_id')
    op.drop_column('posts', 'processed')
    op.add_column('users', sa.Column('crypt', sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(), nullable=True))
    # ### end Alembic commands ###
    # copy all contents from token to crypt, but now contents encrypted.


def downgrade():
    # Assumes all content from crypt was copied to token, but now not encrypted.
    op.drop_column('users', 'crypt')
    op.add_column('posts', sa.Column('campaign_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.add_column('posts', sa.Column('processed', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'posts', type_='foreignkey')
    op.create_foreign_key('posts_ibfk_2', 'posts', 'campaigns', ['campaign_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('posts_ibfk_1', 'posts', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('posts', 'user_id', existing_type=mysql.INTEGER(display_width=11), nullable=False)
    op.drop_column('posts', 'saved_media')
    op.drop_table('processed_campaigns')
    op.drop_table('post_campaigns')
    # ### end Alembic commands ###
