"""webhook_sink_events.delivery_id: ON DELETE SET NULL

Approval events now link to the webhook_deliveries row that records their real outcome.
With the default NO ACTION, deleting a SAR draft (which cascades to its deliveries) — or
clearing webhook_deliveries — would be blocked by the audit events that reference them.

Revision ID: f1a7c0de0002
Revises: c3ce3e9551d4
Create Date: 2026-10-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f1a7c0de0002'
down_revision: Union[str, None] = 'c3ce3e9551d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK = 'webhook_sink_events_delivery_id_fkey'


def upgrade() -> None:
    op.drop_constraint(_FK, 'webhook_sink_events', type_='foreignkey')
    op.create_foreign_key(_FK, 'webhook_sink_events', 'webhook_deliveries',
                          ['delivery_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint(_FK, 'webhook_sink_events', type_='foreignkey')
    op.create_foreign_key(_FK, 'webhook_sink_events', 'webhook_deliveries',
                          ['delivery_id'], ['id'])
