"""
Replacing: 12b85a538f29, e8648dab8e18, 5608765dc3c8, 80421895c9c1, dca6e235628f
Skipping: b78a734006fc
The work of the skipped one will be done by 02_after_encrypt-20200413185403
Revision ID: 01_squashed-20200413143615
Revises: e8648dab8e18
Create Date: 2020-04-13 18:47:18.000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '01_squashed-20200413143615'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # dca6e235628f # 0
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
    op.drop_constraint('posts_ibfk_2', 'posts', type_='foreignkey')
    op.drop_column('posts', 'processed')
    op.drop_column('posts', 'campaign_id')
    # 80421895c9c1 # 1
    op.alter_column('posts', 'user_id', existing_type=mysql.INTEGER(display_width=11), nullable=True)
    op.drop_constraint('posts_ibfk_1', 'posts', type_='foreignkey')
    op.create_foreign_key(None, 'posts', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    # e8648dab8e18 # 4
    # op.add_column('posts', sa.Column('saved_media', sa.String(length=191), nullable=True))
    # 12b85a538f29 # 5
    # op.drop_column('posts', 'saved_media')
    op.add_column('posts', sa.Column('saved_media', sa.Text(), nullable=True))
    # 5608765dc3c8 # 2
    op.add_column('users', sa.Column('crypt', sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(), nullable=True))
    # ### end Alembic commands ###
    # copy all contents from token to crypt, but now contents encrypted.


def downgrade():
    # Assumes all content from crypt was copied to token, but now not encrypted.
    # 5608765dc3c8 # 2
    op.drop_column('users', 'crypt')
    # 12b85a538f29 # 5
    op.drop_column('posts', 'saved_media')
    # op.add_column('posts', sa.Column('saved_media', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=191), nullable=True))
    # e8648dab8e18 # 4
    # op.drop_column('posts', 'saved_media')
    # 80421895c9c1 # 1
    op.drop_constraint(None, 'posts', type_='foreignkey')
    op.create_foreign_key('posts_ibfk_1', 'posts', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('posts', 'user_id', existing_type=mysql.INTEGER(display_width=11), nullable=False)
    # dca6e235628f # 0
    op.add_column('posts', sa.Column('campaign_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.add_column('posts', sa.Column('processed', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True))
    op.create_foreign_key('posts_ibfk_2', 'posts', 'campaigns', ['campaign_id'], ['id'], ondelete='SET NULL')
    op.drop_table('processed_campaigns')
    op.drop_table('post_campaigns')
    # ### end Alembic commands ###
