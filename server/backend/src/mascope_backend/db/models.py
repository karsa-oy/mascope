"""
SQLAlchemy ORM models for the Mascope application.

This module defines all database models including user management, datasets,
samples, targets, and analysis matches.
"""

from datetime import datetime as dt
from datetime import timezone
from typing import Optional

from fastapi_users.db import (
    SQLAlchemyBaseUserTable,
)
from fastapi_users_db_sqlalchemy.access_token import (
    SQLAlchemyBaseAccessTokenTable,
)
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    event,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.sql.schema import CheckConstraint

from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.api.models.sample.items.config import sample_item_config
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)
from mascope_backend.api.models.dataset.config import dataset_config
from mascope_backend.runtime import runtime


# Naming convention for all constraints and indexes.
# Provides predictable names in Alembic migrations (required for DROP/ALTER operations).
# Convention:
#   ix_ : indexes (auto-generated via index=True or Index())
#   uq_ : unique constraints
#   ck_ : check constraints  (ck_<table>_<constraint_name>)
#   fk_ : foreign keys
#   pk_ : primary keys
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class BaseMixin(object):
    """Mixin providing common utility methods for all models."""

    def to_dict(
        self,
    ):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data


Base = declarative_base(
    cls=BaseMixin,
    metadata=MetaData(naming_convention=NAMING_CONVENTION),
)


class User(SQLAlchemyBaseUserTable[int], Base):
    """User authentication and authorization model."""

    __tablename__ = "user"

    # User table fields required for FastAPI Users. Kept unchanged for easier compatibility.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(length=320), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Custom fields
    username: Mapped[str] = mapped_column(
        String(length=100), unique=True, nullable=False
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("role.role_id", ondelete="SET NULL"), nullable=True
    )
    registered_at: Mapped[dt] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False
    )

    # Relationships
    role = relationship("Role", back_populates="user")
    access_token = relationship(
        "AccessToken", back_populates="user", cascade="all, delete, delete-orphan"
    )

    @classmethod
    async def count_other_owners(cls, session, current_user_id: int) -> int:
        """
        Count number of owner users excluding specified user.

        :param session: SQLAlchemy session
        :param current_user_id: User ID to exclude from count
        :return: Count of other owner users
        """
        from mascope_backend.api.new.auth.config import auth_settings

        query = (
            select(func.count())
            .select_from(User)
            .where(
                User.role_id == auth_settings.ROLE_ACCESS_LEVELS["owner"],
                User.id != current_user_id,
            )
        )
        result = await session.execute(query)
        return result.scalar()


class Role(Base):
    """User role and permissions model."""

    __tablename__ = "role"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(String(50), unique=True)
    permissions: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    user = relationship("User", back_populates="role")


class AccessToken(SQLAlchemyBaseAccessTokenTable[int], Base):
    """
    AccessToken model for storing access tokens linked to user accounts.
    Supports different services for authentication.
    """

    __tablename__ = "access_token"

    token: Mapped[str] = mapped_column(String(length=43), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    service_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[dt] = mapped_column(
        TIMESTAMP(timezone=True),
        index=True,
        nullable=False,
        default=lambda: dt.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="access_token")

    @classmethod
    async def clean_invalid_tokens(cls, session) -> int:
        """
        Clean up tokens with NULL/invalid service names that are not allowed in AccessTokenConfig.

        :param session: SQLAlchemy async session
        :type session: AsyncSession
        :return: Number of deleted tokens
        :rtype: int
        """
        from mascope_backend.api.new.auth.config import auth_settings

        allowed_services = auth_settings.access_token.ALLOWED_SERVICES

        # Find tokens with NULL service names or invalid service names
        stmt = select(cls).where(
            or_(cls.service_name.is_(None), cls.service_name.notin_(allowed_services))
        )

        result = await session.execute(stmt)
        invalid_tokens = result.scalars().all()

        if invalid_tokens:
            for token in invalid_tokens:
                await session.delete(token)
            await session.commit()

        # Return number of deleted tokens
        return len(invalid_tokens)


class Dataset(Base):
    """Dataset container for organizing sample batches."""

    __tablename__ = "dataset"

    dataset_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    dataset_name: Mapped[str] = mapped_column(String(256))
    dataset_description: Mapped[Optional[str]] = mapped_column(Text)
    dataset_type: Mapped[str] = mapped_column(
        String(64),
        server_default=text(f"'{dataset_config.DEFAULT_DATASET_TYPE}'"),
    )
    locked: Mapped[int] = mapped_column(
        Integer,
        server_default=text(f"'{dataset_config.DEFAULT_LOCKED_STATUS}'"),
    )
    instrument: Mapped[Optional[str]] = mapped_column(String(64))
    icon: Mapped[Optional[dict]] = mapped_column(JSON)
    dataset_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    dataset_utc_modified: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    # Relationships
    sample_batch = relationship(
        "SampleBatch", back_populates="dataset", cascade="all, delete, delete-orphan"
    )


class SampleBatch(Base):
    """Sample batch grouping related samples for analysis."""

    __tablename__ = "sample_batch"

    sample_batch_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("dataset.dataset_id", ondelete="CASCADE"),
    )
    sample_batch_name: Mapped[str] = mapped_column(String(256))
    sample_batch_description: Mapped[Optional[str]] = mapped_column(Text)
    sample_batch_type: Mapped[str] = mapped_column(
        String(64),
        server_default=text(f"'{sample_batch_config.DEFAULT_SAMPLE_BATCH_TYPE}'"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        server_default=text(f"'{sample_batch_config.DEFAULT_SAMPLE_BATCH_STATUS}'"),
    )
    locked: Mapped[int] = mapped_column(
        Integer,
        server_default=text(f"'{sample_batch_config.DEFAULT_LOCKED_STATUS}'"),
    )
    polarity: Mapped[str] = mapped_column(
        String(4),
        server_default=text(f"'{sample_batch_config.ANALYSIS_POLARITY}'"),
    )
    sample_batch_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    sample_batch_utc_modified: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    # Relationships
    dataset = relationship("Dataset", back_populates="sample_batch")
    sample_items = relationship(
        "SampleItem",
        back_populates="sample_batch",
        cascade="all, delete, delete-orphan",
    )
    target_collection = relationship(
        "TargetCollectionInSampleBatch",
        back_populates="sample_batch",
        cascade="all, delete, delete-orphan",
    )


@event.listens_for(SampleBatch, "after_insert")
@event.listens_for(SampleBatch, "after_update")
@event.listens_for(SampleBatch, "after_delete")
def update_dataset_on_sample_batch_change(mapper, connection, target):
    """Update Dataset timestamp when SampleBatch changes"""
    if target.dataset_id:
        stmt = (
            update(Dataset)
            .where(Dataset.dataset_id == target.dataset_id)
            .values(dataset_utc_modified=dt.now(timezone.utc))
        )
        connection.execute(stmt)
        runtime.logger.debug(
            f"Updated Dataset '{target.dataset_id}' timestamp due to SampleBatch change."
        )


@event.listens_for(SampleBatch, "before_update")
def update_modified_timestamp(mapper, connection, target):
    """Automatically update modification timestamp when SampleBatch is updated."""
    target.sample_batch_utc_modified = dt.now(timezone.utc)


class SampleFile(Base):
    """
    Represents raw acquisition files.

    Each sample file corresponds to a single data file in the filestore.
    Contains metadata about the instrument, calibration, and measurement parameters.

    Datetime columns:
      - datetime:     Instrument local time, stored as TIMESTAMP WITHOUT TIME ZONE.
                      Preserves the literal value recorded by the instrument.
      - datetime_utc: UTC equivalent, stored as TIMESTAMP WITH TIME ZONE.
                      Use this for all time-based calculations and comparisons.
    """

    __tablename__ = "sample_file"

    sample_file_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    instrument_function_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("instrument_function.instrument_function_id", ondelete="SET NULL"),
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(256), unique=True)
    instrument: Mapped[str] = mapped_column(String(64))
    method_file: Mapped[Optional[str]] = mapped_column(String(512))
    datetime: Mapped[dt] = mapped_column(
        TIMESTAMP(timezone=False),
        nullable=False,  # stored literal local time
    )
    datetime_utc: Mapped[dt] = mapped_column(TIMESTAMP(timezone=True))  # stored as UTC
    length: Mapped[float] = mapped_column(Float)
    range: Mapped[dict] = mapped_column(JSON)
    mz_calibration: Mapped[Optional[dict]] = mapped_column(JSON)
    polarity: Mapped[str] = mapped_column(String(4))

    # Relationships
    instrument_function = relationship(
        "InstrumentFunction", back_populates="sample_file"
    )
    sample_items = relationship(
        "SampleItem", back_populates="sample_file", cascade="all, delete, delete-orphan"
    )


class SampleItem(Base):
    """
    Represents a processed sample derived from a sample file.

    Each sample_item is a time-windowed segment of a sample_file that has been
    analyzed and matched against target collections. Multiple sample_items can
    be created from a single sample_file.
    """

    __tablename__ = "sample_item"

    sample_item_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    sample_batch_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_batch.sample_batch_id", ondelete="CASCADE"),
        index=True,
    )
    sample_file_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_file.sample_file_id", ondelete="CASCADE"),
        index=True,
    )
    sample_item_name: Mapped[str] = mapped_column(String(256))
    sample_item_type: Mapped[str] = mapped_column(String(64))
    locked: Mapped[int] = mapped_column(
        Integer,
        server_default=text(f"'{sample_item_config.DEFAULT_LOCKED_STATUS}'"),
    )
    sample_item_attributes: Mapped[Optional[dict]] = mapped_column(JSON)
    filter_id: Mapped[Optional[str]] = mapped_column(String(6))
    tic: Mapped[Optional[float]] = mapped_column(Float)
    polarity: Mapped[Optional[str]] = mapped_column(String(1))
    ionization_mode_id: Mapped[Optional[str]] = mapped_column(
        String(16),
        ForeignKey(
            "ionization_mode.ionization_mode_id",
            ondelete="SET NULL",
        ),
    )
    t0: Mapped[Optional[float]] = mapped_column(Float)
    t1: Mapped[Optional[float]] = mapped_column(Float)
    sample_item_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    sample_item_utc_modified: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    # Relationships
    sample_batch = relationship("SampleBatch", back_populates="sample_items")
    sample_file = relationship("SampleFile", back_populates="sample_items")
    match_sample = relationship(
        "MatchSample",
        back_populates="sample_item",
        cascade="all, delete, delete-orphan",
    )
    match_collection = relationship(
        "MatchCollection",
        back_populates="sample_item",
        cascade="all, delete, delete-orphan",
    )
    match_compound = relationship(
        "MatchCompound",
        back_populates="sample_item",
        cascade="all, delete, delete-orphan",
    )
    match_ion = relationship(
        "MatchIon",
        back_populates="sample_item",
        cascade="all, delete, delete-orphan",
    )
    match_isotope = relationship(
        "MatchIsotope",
        back_populates="sample_item",
        cascade="all, delete, delete-orphan",
    )
    match_rating = relationship(
        "MatchRating",
        back_populates="sample_item",
        cascade="all, delete, delete-orphan",
    )


@event.listens_for(SampleItem, "after_update")
def update_sample_batch_on_sample_item_change(mapper, connection, target):
    """Update SampleBatch timestamp when SampleItem changes."""
    if target.sample_batch_id:
        stmt = (
            update(SampleBatch)
            .where(SampleBatch.sample_batch_id == target.sample_batch_id)
            .values(sample_batch_utc_modified=dt.now(timezone.utc))
        )
        connection.execute(stmt)
        runtime.logger.debug(
            f"Updated SampleBatch '{target.sample_batch_id}' timestamp due to SampleItem change."
        )


class TargetCollection(Base):
    """Collection of target compounds for analysis."""

    __tablename__ = "target_collection"

    target_collection_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    target_collection_name: Mapped[str] = mapped_column(String(256))
    target_collection_description: Mapped[Optional[str]] = mapped_column(Text)
    target_collection_type: Mapped[str] = mapped_column(
        String(64),
        server_default=text(
            f"'{target_collection_config.DEFAULT_TARGET_COLLECTION_TYPE}'"
        ),
    )

    # Relationships
    sample_batch = relationship(
        "TargetCollectionInSampleBatch",
        back_populates="target_collection",
        cascade="all, delete, delete-orphan",
    )
    target_compound = relationship(
        "TargetCompoundInTargetCollection",
        back_populates="target_collection",
        cascade="all, delete, delete-orphan",
    )
    match_collection = relationship(
        "MatchCollection",
        back_populates="target_collection",
        cascade="all, delete, delete-orphan",
    )
    calibration_ionization_modes = relationship(
        "IonizationMode",
        foreign_keys="IonizationMode.calibration_collection_id",
        back_populates="calibration_collection",
    )
    diagnostic_ionization_modes = relationship(
        "IonizationMode",
        foreign_keys="IonizationMode.diagnostic_collection_id",
        back_populates="diagnostic_collection",
    )


class TargetCollectionInSampleBatch(Base):
    """Junction table linking target collections to sample batches."""

    __tablename__ = "target_collection_in_sample_batch"

    target_collection_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_collection.target_collection_id", ondelete="CASCADE"),
        primary_key=True,
    )
    sample_batch_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_batch.sample_batch_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    target_collection = relationship("TargetCollection", back_populates="sample_batch")
    sample_batch = relationship("SampleBatch", back_populates="target_collection")


class TargetCompoundInTargetCollection(Base):
    """Junction table linking target compounds to target collections."""

    __tablename__ = "target_compound_in_target_collection"

    target_compound_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_compound.target_compound_id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_collection_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_collection.target_collection_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    target_collection = relationship(
        "TargetCollection", back_populates="target_compound"
    )
    target_compound = relationship("TargetCompound", back_populates="target_collection")


class TargetCompound(Base):
    """Target compound definition."""

    __tablename__ = "target_compound"

    target_compound_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    target_compound_name: Mapped[Optional[str]] = mapped_column(Text)
    target_compound_formula: Mapped[str] = mapped_column(String(256))
    cas_number: Mapped[Optional[str]] = mapped_column(String(12))

    # Relationships
    target_collection = relationship(
        "TargetCompoundInTargetCollection",
        back_populates="target_compound",
        cascade="all, delete, delete-orphan",
    )
    target_ion = relationship(
        "TargetIon",
        back_populates="target_compound",
        cascade="all, delete, delete-orphan",
    )
    match_compound = relationship(
        "MatchCompound",
        back_populates="target_compound",
        cascade="all, delete, delete-orphan",
    )


class TargetIon(Base):
    """Target ion derived from target compound and ionization mechanism."""

    __tablename__ = "target_ion"

    target_ion_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    target_compound_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_compound.target_compound_id", ondelete="CASCADE"),
    )
    ionization_mechanism_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("ionization_mechanism.ionization_mechanism_id", ondelete="CASCADE"),
        index=True,
    )
    target_ion_formula: Mapped[str] = mapped_column(String(256))
    filter_params: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    target_compound = relationship("TargetCompound", back_populates="target_ion")
    ionization_mechanism = relationship(
        "IonizationMechanism", back_populates="target_ion"
    )
    target_isotope = relationship(
        "TargetIsotope",
        back_populates="target_ion",
        cascade="all, delete, delete-orphan",
    )
    match_ion = relationship(
        "MatchIon",
        back_populates="target_ion",
        cascade="all, delete, delete-orphan",
    )
    match_rating = relationship(
        "MatchRating",
        back_populates="target_ion",
        cascade="all, delete, delete-orphan",
    )


class IonizationMechanism(Base):
    """Ionization mechanism table."""

    __tablename__ = "ionization_mechanism"

    ionization_mechanism_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    ionization_mechanism_polarity: Mapped[str] = mapped_column(String(1))
    ionization_mechanism: Mapped[str] = mapped_column(String(256), unique=True)

    # Relationships
    target_ion = relationship(
        "TargetIon",
        back_populates="ionization_mechanism",
        cascade="all, delete, delete-orphan",
    )


class IonizationMode(Base):
    """Ionization mode configuration."""

    __tablename__ = "ionization_mode"

    ionization_mode_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    ionization_mode_name: Mapped[str] = mapped_column(String(256))
    ionization_mode_token: Mapped[Optional[str]] = mapped_column(
        String(256), unique=True
    )
    ionization_mode_polarity: Mapped[str] = mapped_column(String(1))
    ionization_mechanism_ids: Mapped[list[str]] = mapped_column(JSON)
    calibration_collection_id: Mapped[Optional[str]] = mapped_column(
        String(16),
        ForeignKey("target_collection.target_collection_id", ondelete="SET NULL"),
    )
    diagnostic_collection_id: Mapped[Optional[str]] = mapped_column(
        String(16),
        ForeignKey("target_collection.target_collection_id", ondelete="SET NULL"),
    )

    # Relationships
    calibration_collection = relationship(
        "TargetCollection",
        foreign_keys=[calibration_collection_id],
        back_populates="calibration_ionization_modes",
    )
    diagnostic_collection = relationship(
        "TargetCollection",
        foreign_keys=[diagnostic_collection_id],
        back_populates="diagnostic_ionization_modes",
    )


class TargetIsotope(Base):
    """Target isotope table."""

    __tablename__ = "target_isotope"

    target_isotope_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    target_ion_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey(
            "target_ion.target_ion_id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    target_isotope_formula: Mapped[str] = mapped_column(
        String(4096)
    )  # lower length limit #1360 https://github.com/karsa-oy/mascope/issues/1360
    mz: Mapped[float] = mapped_column(Float)
    relative_abundance: Mapped[float] = mapped_column(Float)
    resolution: Mapped[str] = mapped_column(String(8))

    # Relationships
    target_ion = relationship("TargetIon", back_populates="target_isotope")
    match_isotope = relationship(
        "MatchIsotope",
        back_populates="target_isotope",
        cascade="all, delete, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "relative_abundance >= 0 AND relative_abundance <= 1",
            name="relative_abundance_range",
        ),
    )


class MatchSample(Base):
    """Sample-level match result."""

    __tablename__ = "match_sample"

    match_sample_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sample_item_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        index=True,
    )
    match_score: Mapped[float] = mapped_column(Float)
    match_category: Mapped[int] = mapped_column(Integer)
    sample_peak_intensity_sum: Mapped[float] = mapped_column(Float)
    match_sample_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    match_sample_utc_modified: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    # Relationships
    sample_item = relationship("SampleItem", back_populates="match_sample")

    __table_args__ = (
        CheckConstraint("match_score BETWEEN 0 AND 1", name="match_score_range"),
        CheckConstraint("match_category BETWEEN 0 AND 2", name="match_category_range"),
    )


class MatchCollection(Base):
    """Collection-level match result."""

    __tablename__ = "match_collection"

    match_collection_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sample_item_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        index=True,
    )
    target_collection_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_collection.target_collection_id", ondelete="CASCADE"),
    )
    match_score: Mapped[float] = mapped_column(Float)
    match_category: Mapped[int] = mapped_column(Integer)
    sample_peak_intensity_sum: Mapped[float] = mapped_column(Float)
    match_collection_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    match_collection_utc_modified: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    # Relationships
    sample_item = relationship("SampleItem", back_populates="match_collection")
    target_collection = relationship(
        "TargetCollection", back_populates="match_collection"
    )

    # Indexes
    __table_args__ = (
        CheckConstraint("match_score BETWEEN 0 AND 1", name="match_score_range"),
        CheckConstraint("match_category BETWEEN 0 AND 2", name="match_category_range"),
    )


class MatchCompound(Base):
    """Compound-level match result."""

    __tablename__ = "match_compound"

    match_compound_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sample_item_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        index=True,
    )
    target_compound_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_compound.target_compound_id", ondelete="CASCADE"),
    )
    match_score: Mapped[float] = mapped_column(Float)
    match_category: Mapped[int] = mapped_column(Integer)
    sample_peak_intensity_sum: Mapped[float] = mapped_column(Float)
    match_compound_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    match_compound_utc_modified: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    # Relationships
    sample_item = relationship("SampleItem", back_populates="match_compound")
    target_compound = relationship("TargetCompound", back_populates="match_compound")

    # Indexes
    __table_args__ = (
        CheckConstraint("match_score BETWEEN 0 AND 1", name="match_score_range"),
        CheckConstraint("match_category BETWEEN 0 AND 2", name="match_category_range"),
    )


class MatchIon(Base):
    """Ion-level match result."""

    __tablename__ = "match_ion"

    match_ion_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sample_item_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        index=True,
    )
    target_ion_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_ion.target_ion_id", ondelete="CASCADE"),
        index=True,
    )
    match_score: Mapped[float] = mapped_column(Float)
    match_category: Mapped[int] = mapped_column(Integer)
    sample_peak_intensity_sum: Mapped[float] = mapped_column(Float)
    match_ion_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    match_ion_utc_modified: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    # Relationships
    sample_item = relationship("SampleItem", back_populates="match_ion")
    target_ion = relationship("TargetIon", back_populates="match_ion")

    __table_args__ = (
        CheckConstraint("match_score BETWEEN 0 AND 1", name="match_score_range"),
        CheckConstraint("match_category BETWEEN 0 AND 2", name="match_category_range"),
    )


class MatchRating(Base):
    """User rating for match quality."""

    __tablename__ = "match_rating"

    match_rating_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sample_item_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
    )
    target_ion_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_ion.target_ion_id", ondelete="CASCADE"),
    )
    match_rating_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    rating: Mapped[int] = mapped_column(Integer)
    checklist: Mapped[Optional[dict]] = mapped_column(JSON)
    environment: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    sample_item = relationship("SampleItem", back_populates="match_rating")
    target_ion = relationship("TargetIon", back_populates="match_rating")

    __table_args__ = (CheckConstraint("rating BETWEEN 0 AND 2", name="rating_range"),)


class MatchIsotope(Base):
    """Isotope-level match result."""

    __tablename__ = "match_isotope"

    match_isotope_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    target_isotope_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("target_isotope.target_isotope_id", ondelete="CASCADE"),
        index=True,
    )
    sample_item_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        index=True,
    )
    sample_peak_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
    )
    sample_peak_mz: Mapped[float] = mapped_column(Float)
    sample_peak_intensity: Mapped[float] = mapped_column(Float)
    sample_peak_intensity_relative: Mapped[float] = mapped_column(Float)
    sample_peak_tof: Mapped[float] = mapped_column(Float)
    match_abundance_error: Mapped[float] = mapped_column(Float)
    match_mz_error: Mapped[float] = mapped_column(Float)
    match_score: Mapped[float] = mapped_column(Float)
    match_isotope_utc_created: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    match_isotope_utc_modified: Mapped[Optional[dt]] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    # Relationships
    sample_item = relationship("SampleItem", back_populates="match_isotope")
    target_isotope = relationship("TargetIsotope", back_populates="match_isotope")

    __table_args__ = (
        CheckConstraint("match_score BETWEEN 0 AND 1", name="match_score_range"),
    )


class AttributeTemplate(Base):
    """Attribute template for additional sample metadata."""

    __tablename__ = "attribute_template"

    attribute_template_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    type: Mapped[Optional[str]] = mapped_column(String(64))
    template: Mapped[Optional[dict]] = mapped_column(JSON)


class InstrumentFunction(Base):
    """Instrument function parameters."""

    __tablename__ = "instrument_function"

    instrument_function_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    instrument: Mapped[str] = mapped_column(String(64))
    method_file: Mapped[str] = mapped_column(String(512))
    datetime_utc: Mapped[dt] = mapped_column(TIMESTAMP(timezone=True))
    peakshape: Mapped[Optional[dict]] = mapped_column(JSON)
    resolution_function: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    sample_file = relationship("SampleFile", back_populates="instrument_function")


__all__ = [
    "Base",
    "User",
    "Role",
    "AccessToken",
    "Dataset",
    "SampleBatch",
    "SampleFile",
    "SampleItem",
    "TargetCollection",
    "TargetCollectionInSampleBatch",
    "TargetCompound",
    "TargetCompoundInTargetCollection",
    "TargetIon",
    "TargetIsotope",
    "IonizationMechanism",
    "IonizationMode",
    "MatchSample",
    "MatchCollection",
    "MatchCompound",
    "MatchIon",
    "MatchIsotope",
    "MatchRating",
    "AttributeTemplate",
    "InstrumentFunction",
]
