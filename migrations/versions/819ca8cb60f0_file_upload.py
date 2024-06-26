"""File Upload

Revision ID: 819ca8cb60f0
Revises: c1455ca7e59f
Create Date: 2024-04-20 17:26:44.574277

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '819ca8cb60f0'
down_revision = 'c1455ca7e59f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meeting_priority', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embeddings_index', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meeting_priority', schema=None) as batch_op:
        batch_op.drop_column('embeddings_index')

    # ### end Alembic commands ###
