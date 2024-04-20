"""Invitations

Revision ID: d5f04ceb19d8
Revises: ab26ed2c83d3
Create Date: 2024-04-20 13:21:28.641818

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5f04ceb19d8'
down_revision = 'ab26ed2c83d3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('meeting_invitations',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('meeting_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['meeting_id'], ['meeting.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'meeting_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('meeting_invitations')
    # ### end Alembic commands ###