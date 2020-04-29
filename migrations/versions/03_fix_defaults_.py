"""empty message

Revision ID: 03_fix_defaults
Revises: after_encrypt
Create Date: 2020-04-14 16:25:11.683450

"""
from alembic import op
# import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '03_fix_defaults'
down_revision = 'after_encrypt'
branch_labels = ('fix-defaults',)
depends_on = None


def upgrade():
    op.alter_column('posts', 'comments_count',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'like_count',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'impressions',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'reach',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'engagement',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'saved',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'video_views',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'exits',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'replies',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'taps_forward',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('posts', 'taps_back',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('onlinefollowers', 'value',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    op.alter_column('insights', 'value',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=True,
                    nullable=False,
                    default=0)
    # end Alebic commands.


def downgrade():
    op.alter_column('posts', 'comments_count',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'like_count',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'impressions',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'reach',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'engagement',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'saved',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'video_views',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'exits',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'replies',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'taps_forward',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('posts', 'taps_back',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('onlinefollowers', 'value',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    op.alter_column('insights', 'value',
                    existing_type=mysql.INTEGER(11),
                    existing_nullable=False,
                    nullable=True,
                    existing_default=0,
                    default=None)
    # end Alebic commands.
