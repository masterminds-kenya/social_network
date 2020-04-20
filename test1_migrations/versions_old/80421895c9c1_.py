"""empty message

Revision ID: 80421895c9c1
Revises: dca6e235628f
Create Date: 2020-03-17 05:37:28.299589

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '80421895c9c1'
down_revision = 'dca6e235628f'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('posts', 'user_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    op.drop_constraint('posts_ibfk_1', 'posts', type_='foreignkey')
    op.create_foreign_key(None, 'posts', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    # ### end Alembic commands ###


def downgrade():
    op.drop_constraint(None, 'posts', type_='foreignkey')
    op.create_foreign_key('posts_ibfk_1', 'posts', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('posts', 'user_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
    # ### end Alembic commands ###
