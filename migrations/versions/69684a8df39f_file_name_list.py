"""File name list

Revision ID: 69684a8df39f
Revises: 819ca8cb60f0
Create Date: 2024-04-20 17:59:24.575275

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '69684a8df39f'
down_revision = '819ca8cb60f0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meeting_priority', schema=None) as batch_op:
        batch_op.add_column(sa.Column('file_name_list', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meeting_priority', schema=None) as batch_op:
        batch_op.drop_column('file_name_list')

    # ### end Alembic commands ###
