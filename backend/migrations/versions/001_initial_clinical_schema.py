"""Initial clinical schema — patients, medications, reconciliation_results, data_quality_results.

Revision ID: 001
Revises:
Create Date: 2026-04-07 00:00:00.000000

Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all clinical domain tables.

    SPEC-0001 REQ "SQLAlchemy ORM Data Layer":
      WHEN `flask db upgrade` is run against an empty database
      THEN all tables are created without errors and the schema
           matches the current ORM model definitions.
    """
    # --- patients ---
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- medications ---
    op.create_table(
        "medications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("system", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("last_updated", sa.Date(), nullable=True),
        sa.Column("last_filled", sa.Date(), nullable=True),
        sa.Column("source_reliability", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- reconciliation_results ---
    # Stores hybrid-scored reconciliation output with timestamp + patient reference.
    # SPEC-0001 REQ "SQLAlchemy ORM Data Layer": result MUST be saved with timestamp
    # and patient reference.
    op.create_table(
        "reconciliation_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("reconciled_medication", sa.String(length=500), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("clinical_safety_check", sa.String(length=20), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("recommended_actions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- data_quality_results ---
    op.create_table(
        "data_quality_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("completeness", sa.Float(), nullable=False),
        sa.Column("validity", sa.Float(), nullable=False),
        sa.Column("consistency", sa.Float(), nullable=False),
        sa.Column("timeliness", sa.Float(), nullable=False),
        sa.Column("issues_detected", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all clinical domain tables in reverse dependency order."""
    op.drop_table("data_quality_results")
    op.drop_table("reconciliation_results")
    op.drop_table("medications")
    op.drop_table("patients")
