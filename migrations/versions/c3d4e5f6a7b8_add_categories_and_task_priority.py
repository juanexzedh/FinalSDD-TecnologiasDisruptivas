"""add categories and task priority

Revision ID: c3d4e5f6a7b8
Revises: 9e8a84471a2a
Create Date: 2026-10-17 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = '9e8a84471a2a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_categories_user_id_name')
    )
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_categories_user_id'), ['user_id'], unique=False)

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('priority', sa.String(length=20), server_default='medium', nullable=False))
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_tasks_category_id_categories', 'categories', ['category_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_tasks_user_id_priority', ['user_id', 'priority'], unique=False)
        batch_op.create_index('ix_tasks_category_id', ['category_id'], unique=False)


def downgrade():
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_index('ix_tasks_category_id')
        batch_op.drop_index('ix_tasks_user_id_priority')
        batch_op.drop_constraint('fk_tasks_category_id_categories', type_='foreignkey')
        batch_op.drop_column('category_id')
        batch_op.drop_column('priority')

    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_categories_user_id'))

    op.drop_table('categories')
