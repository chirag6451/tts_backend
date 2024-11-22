"""add_invitation_status_to_team_members

Revision ID: fdcc0cf922be
Revises: 64578c036b4a
Create Date: 2024-11-22 18:17:16.821570

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdcc0cf922be'
down_revision: Union[str, None] = '64578c036b4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a temporary table with the new structure
    op.create_table(
        'team_members_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('invitation_status', sa.Enum('PENDING', 'ACCEPTED', 'DECLINED', name='invitationstatus'), nullable=False, server_default='PENDING'),
        sa.Column('invited_by_id', sa.Integer(), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Copy data from the old table
    op.execute('''
        INSERT INTO team_members_new (id, team_id, user_id, role, created_at, updated_at)
        SELECT id, team_id, user_id, role, created_at, updated_at
        FROM team_members;
    ''')
    
    # Drop the old table
    op.drop_table('team_members')
    
    # Rename the new table to the original name
    op.rename_table('team_members_new', 'team_members')


def downgrade() -> None:
    # Create a temporary table with the old structure
    op.create_table(
        'team_members_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Copy data from the current table
    op.execute('''
        INSERT INTO team_members_old (id, team_id, user_id, role, created_at, updated_at)
        SELECT id, team_id, user_id, role, created_at, updated_at
        FROM team_members;
    ''')
    
    # Drop the current table
    op.drop_table('team_members')
    
    # Rename the old table to the original name
    op.rename_table('team_members_old', 'team_members')
    
    # Drop the enum type
    sa.Enum(name='invitationstatus').drop(op.get_bind(), checkfirst=True)
