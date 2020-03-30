"""empty message

Revision ID: e8648dab8e18
Revises: b78a734006fc
Create Date: 2020-03-29 19:21:32.853344

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8648dab8e18'
down_revision = 'b78a734006fc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('posts', sa.Column('saved_media', sa.String(length=191), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('posts', 'saved_media')
    # ### end Alembic commands ###
