from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    event,
    TIMESTAMP,
    Column,
    Boolean,
    Index,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql.schema import CheckConstraint
from sqlalchemy.orm import declarative_base
from fastapi_users.db import (
    SQLAlchemyBaseUserTable,
)
from fastapi_users_db_sqlalchemy.access_token import (
    SQLAlchemyBaseAccessTokenTable,
)
from mascope_backend.api.models.workspace.config import workspace_config
from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.api.models.sample.items.config import sample_item_config
from mascope_backend.api.models.ionization_mechanisms.config import (
    ionization_mechanism_config,
)
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)
from mascope_backend.runtime import runtime


class BaseMixin(object):
    def to_dict(
        self,
    ):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data


Base = declarative_base(cls=BaseMixin)


class User(SQLAlchemyBaseUserTable[int], Base):
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
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.role_id", ondelete="SET NULL"), nullable=True
    )
    registered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Define relationships
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
            select(func.count())  # pylint: disable=not-callable
            .select_from(User)
            .where(
                User.role_id == auth_settings.ROLE_ACCESS_LEVELS["owner"],
                User.id != current_user_id,
            )
        )
        result = await session.execute(query)
        return result.scalar()


class Role(Base):
    __tablename__ = "role"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(
        String(length=50), unique=True, nullable=False
    )
    permissions: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Define relationships
    user = relationship("User", back_populates="role")


class AccessToken(SQLAlchemyBaseAccessTokenTable[int], Base):
    """
    AccessToken model for storing access tokens linked to user accounts.
    Supports different servicess for authentication.
    """

    __tablename__ = "access_token"

    token: Mapped[str] = mapped_column(String(length=43), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    service_name: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        index=True,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Define relationships
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


class Workspace(Base):
    __tablename__ = "workspace"
    workspace_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    workspace_name: Mapped[str] = mapped_column(String(256), nullable=False)
    workspace_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workspace_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=text(f"{workspace_config.DEFAULT_WORKSPACE_TYPE}"),
    )
    locked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text(f"{workspace_config.DEFAULT_LOCKED_STATUS}"),
    )
    instrument: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    icon: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    workspace_utc_created: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    workspace_utc_modified: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    # Define relationships
    sample_batch = relationship(
        "SampleBatch", back_populates="workspace", cascade="all, delete, delete-orphan"
    )


class SampleBatch(Base):
    __tablename__ = "sample_batch"
    sample_batch_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_batch_name: Mapped[str] = mapped_column(String, nullable=False)
    sample_batch_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sample_batch_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=text(f"{sample_batch_config.DEFAULT_SAMPLE_BATCH_TYPE}"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text(f"{sample_batch_config.DEFAULT_SAMPLE_BATCH_STATUS}"),
    )
    locked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text(f"{sample_batch_config.DEFAULT_LOCKED_STATUS}"),
    )
    polarity: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
        server_default=text(f"'{sample_batch_config.ANALYSIS_POLARITY}'"),
    )
    sample_batch_utc_created: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    sample_batch_utc_modified: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP, nullable=True
    )

    # Define relationships
    workspace = relationship("Workspace", back_populates="sample_batch")
    sample_item = relationship(
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
def update_workspace_on_sample_batch_change(mapper, connection, target):
    """Update Workspace timestamp when SampleBatch changes"""
    if target.workspace_id:
        stmt = (
            update(Workspace)
            .where(Workspace.workspace_id == target.workspace_id)
            .values(workspace_utc_modified=datetime.now(timezone.utc))
        )
        connection.execute(stmt)
        runtime.logger.debug(
            f"Updated Workspace '{target.workspace_id}' timestamp due to SampleBatch change."
        )


@event.listens_for(SampleBatch, "before_update")
def update_modified_timestamp(mapper, connection, target):
    """Automatically update modification timestamp when SampleBatch is updated."""
    target.sample_batch_utc_modified = datetime.now(timezone.utc)


class SampleItem(Base):
    __tablename__ = "sample_item"
    sample_item_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    sample_batch_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_batch.sample_batch_id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    sample_item_name: Mapped[str] = mapped_column(String(256), nullable=False)
    sample_item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    locked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text(f"{sample_item_config.DEFAULT_LOCKED_STATUS}"),
    )
    sample_item_attributes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    filter_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    tic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    polarity: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    ionization_mode_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey(
            "ionization_mode.ionization_mode_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    t0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    t1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_item_utc_created: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    sample_item_utc_modified: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP, nullable=True
    )

    # Define relationships
    sample_batch = relationship("SampleBatch", back_populates="sample_item")
    # TODO_db issue #376
    # sample_file = relationship(
    #     "SampleFile", back_populates="sample_item", foreign_keys=[filename]
    # )
    sample_file = relationship(
        "SampleFile",
        primaryjoin="foreign(SampleItem.filename)==remote(SampleFile.filename)",
        viewonly=True,
    )
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

    # Define indexes
    __table_args__ = (Index("idx_sample_item_sample_batch", "sample_batch_id"),)


@event.listens_for(SampleItem, "after_update")
def update_sample_batch_on_sample_item_change(mapper, connection, target):
    """Update SampleBatch timestamp when SampleItem changes."""
    if target.sample_batch_id:
        stmt = (
            update(SampleBatch)
            .where(SampleBatch.sample_batch_id == target.sample_batch_id)
            .values(sample_batch_utc_modified=datetime.now(timezone.utc))
        )
        connection.execute(stmt)
        runtime.logger.debug(
            f"Updated SampleBatch '{target.sample_batch_id}' timestamp due to SampleItem change."
        )


class SampleFile(Base):
    __tablename__ = "sample_file"
    sample_file_id = Column(String(16), nullable=False, primary_key=True)
    instrument_function_id = Column(
        String(32),
        ForeignKey("instrument_function.instrument_function_id", ondelete="SET NULL"),
        nullable=True,
    )
    filename = Column(String(256), nullable=False, unique=True)
    instrument = Column(String(64))
    method_file = Column(String(256), nullable=True)
    datetime = Column(TIMESTAMP)
    datetime_utc = Column(TIMESTAMP)
    length = Column(Float)
    range = Column(JSON)
    mz_calibration = Column(JSON)
    polarity = Column(String(4))

    # Define relationships
    instrument_function = relationship(
        "InstrumentFunction", back_populates="sample_file"
    )
    # sample_item = relationship("SampleItem", back_populates="sample_file") # TODO_db issue #376


class TargetCollection(Base):
    __tablename__ = "target_collection"
    target_collection_id = Column(String(16), nullable=False, primary_key=True)
    target_collection_name = Column(String(256), nullable=False)
    target_collection_description = Column(Text)
    target_collection_type = Column(
        String(64),
        nullable=False,
        server_default=text(
            f"{target_collection_config.DEFAULT_TARGET_COLLECTION_TYPE}"
        ),
    )

    # Define relationships
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


class TargetCollectionInSampleBatch(Base):
    __tablename__ = "target_collection_in_sample_batch"
    target_collection_id = Column(
        String(16),
        ForeignKey("target_collection.target_collection_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    sample_batch_id = Column(
        String(16),
        ForeignKey("sample_batch.sample_batch_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Define relationships
    target_collection = relationship("TargetCollection", back_populates="sample_batch")
    sample_batch = relationship("SampleBatch", back_populates="target_collection")


class TargetCompoundInTargetCollection(Base):
    __tablename__ = "target_compound_in_target_collection"
    target_compound_id = Column(
        String(16),
        ForeignKey("target_compound.target_compound_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    target_collection_id = Column(
        String(16),
        ForeignKey("target_collection.target_collection_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Define relationships
    target_collection = relationship(
        "TargetCollection", back_populates="target_compound"
    )
    target_compound = relationship("TargetCompound", back_populates="target_collection")


class TargetCompound(Base):
    __tablename__ = "target_compound"
    target_compound_id = Column(String(16), nullable=False, primary_key=True)
    target_compound_name = Column(Text)
    target_compound_formula = Column(String(256), nullable=False)
    cas_number = Column(String(12))

    # Define relationships
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
    __tablename__ = "target_ion"
    target_ion_id = Column(String(16), nullable=False, primary_key=True)
    target_compound_id = Column(
        String(16),
        ForeignKey("target_compound.target_compound_id", ondelete="CASCADE"),
        nullable=False,
    )
    ionization_mechanism_id = Column(
        String(16),
        ForeignKey(
            "ionization_mechanism.ionization_mechanism_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    target_ion_formula = Column(String(256), nullable=False)
    filter_params = Column(JSON)

    # Define relationships
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

    # Define indexes
    __table_args__ = (
        Index("idx_target_ion_ionization_mechanism", "ionization_mechanism_id"),
    )


class IonizationMechanism(Base):
    __tablename__ = "ionization_mechanism"

    ionization_mechanism_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    ionization_mechanism_polarity: Mapped[str] = mapped_column(
        String(1), nullable=False
    )
    ionization_mechanism: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    reagent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_default: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text(f"{ionization_mechanism_config.DEFAULT_IS_DEFAULT_STATUS}"),
    )

    # Define relationships
    target_ion = relationship(
        "TargetIon",
        back_populates="ionization_mechanism",
        cascade="all, delete, delete-orphan",
    )


class IonizationMode(Base):
    __tablename__ = "ionization_mode"

    ionization_mode_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    ionization_mode_name: Mapped[str] = mapped_column(String(256), nullable=False)
    ionization_mode_token: Mapped[Optional[str]] = mapped_column(
        String(256), unique=True, nullable=True
    )
    ionization_mode_polarity: Mapped[str] = mapped_column(String(1), nullable=False)
    ionization_mechanism_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    calibration_collection_id: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True
    )
    diagnostic_collection_id: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True
    )


class TargetIsotope(Base):
    __tablename__ = "target_isotope"
    target_isotope_id = Column(String(16), nullable=False, primary_key=True)
    target_ion_id = Column(
        String(16),
        ForeignKey(
            "target_ion.target_ion_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    mz = Column(Float, nullable=False)
    relative_abundance = Column(
        Float,
        CheckConstraint("relative_abundance >= 0 AND relative_abundance <= 1"),
        nullable=False,
    )
    resolution = Column(
        String(8),
        nullable=False,
    )

    # Define relationships
    target_ion = relationship("TargetIon", back_populates="target_isotope")
    match_isotope = relationship(
        "MatchIsotope",
        back_populates="target_isotope",
        cascade="all, delete, delete-orphan",
    )


class MatchSample(Base):
    __tablename__ = "match_sample"
    match_sample_id = Column(String(32), nullable=False, primary_key=True)
    sample_item_id = Column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        nullable=False,
    )
    match_score = Column(
        Float, CheckConstraint("match_score BETWEEN 0 AND 1"), nullable=False
    )
    match_category = Column(
        Integer, CheckConstraint("match_category BETWEEN 0 AND 2"), nullable=False
    )
    sample_peak_intensity_sum = Column(Float, nullable=False)
    match_sample_utc_created = Column(TIMESTAMP)
    match_sample_utc_modified = Column(TIMESTAMP)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match_sample")

    # Define indexes
    __table_args__ = (Index("idx_match_sample_sample_item", "sample_item_id"),)


class MatchCollection(Base):
    __tablename__ = "match_collection"
    match_collection_id = Column(String(32), nullable=False, primary_key=True)
    sample_item_id = Column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        nullable=False,
    )
    target_collection_id = Column(
        String(16),
        ForeignKey("target_collection.target_collection_id", ondelete="CASCADE"),
        nullable=False,
    )
    match_score = Column(
        Float, CheckConstraint("match_score BETWEEN 0 AND 1"), nullable=False
    )
    match_category = Column(
        Integer, CheckConstraint("match_category BETWEEN 0 AND 2"), nullable=False
    )
    sample_peak_intensity_sum = Column(Float, nullable=False)
    match_collection_utc_created = Column(TIMESTAMP)
    match_collection_utc_modified = Column(TIMESTAMP)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match_collection")
    target_collection = relationship(
        "TargetCollection", back_populates="match_collection"
    )

    # Define indexes
    __table_args__ = (Index("idx_match_collection_sample_item", "sample_item_id"),)


class MatchCompound(Base):
    __tablename__ = "match_compound"
    match_compound_id = Column(String(32), nullable=False, primary_key=True)
    sample_item_id = Column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        nullable=False,
    )
    target_compound_id = Column(
        String(16),
        ForeignKey("target_compound.target_compound_id", ondelete="CASCADE"),
        nullable=False,
    )
    match_score = Column(
        Float, CheckConstraint("match_score BETWEEN 0 AND 1"), nullable=False
    )
    match_category = Column(
        Integer, CheckConstraint("match_category BETWEEN 0 AND 2"), nullable=False
    )
    sample_peak_intensity_sum = Column(Float, nullable=False)
    match_compound_utc_created = Column(TIMESTAMP)
    match_compound_utc_modified = Column(TIMESTAMP)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match_compound")
    target_compound = relationship("TargetCompound", back_populates="match_compound")

    # Define indexes
    __table_args__ = (Index("idx_match_compound_sample_item", "sample_item_id"),)


class MatchIon(Base):
    __tablename__ = "match_ion"
    match_ion_id = Column(String(32), nullable=False, primary_key=True)
    sample_item_id = Column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        nullable=False,
    )
    target_ion_id = Column(
        String(16),
        ForeignKey("target_ion.target_ion_id", ondelete="CASCADE"),
        nullable=False,
    )
    match_score = Column(
        Float, CheckConstraint("match_score BETWEEN 0 AND 1"), nullable=False
    )
    match_category = Column(
        Integer, CheckConstraint("match_category BETWEEN 0 AND 2"), nullable=False
    )
    sample_peak_intensity_sum = Column(Float, nullable=False)
    match_ion_utc_created = Column(TIMESTAMP)
    match_ion_utc_modified = Column(TIMESTAMP)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match_ion")
    target_ion = relationship("TargetIon", back_populates="match_ion")

    # Define indexes
    __table_args__ = (Index("idx_match_ion_sample_item", "sample_item_id"),)


class MatchRating(Base):
    __tablename__ = "match_rating"
    match_rating_id = Column(String(32), nullable=False, primary_key=True)
    sample_item_id = Column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        nullable=False,
    )
    target_ion_id = Column(
        String(16),
        ForeignKey("target_ion.target_ion_id", ondelete="CASCADE"),
        nullable=False,
    )
    match_rating_utc_created = Column(TIMESTAMP)
    rating = Column(Integer, CheckConstraint("rating BETWEEN 0 AND 2"), nullable=False)
    checklist = Column(JSON)
    environment = Column(JSON)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match_rating")
    target_ion = relationship("TargetIon", back_populates="match_rating")


class MatchIsotope(Base):
    __tablename__ = "match_isotope"
    match_isotope_id = Column(String(32), nullable=False, primary_key=True)
    target_isotope_id = Column(
        String(16),
        ForeignKey("target_isotope.target_isotope_id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_item_id = Column(
        String(16),
        ForeignKey("sample_item.sample_item_id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_peak_id = Column(String(20), nullable=False)
    sample_peak_mz = Column(Float, nullable=False)
    sample_peak_intensity = Column(Float, nullable=False)
    sample_peak_intensity_relative = Column(Float, nullable=False)
    sample_peak_tof = Column(Float, nullable=False)
    match_abundance_error = Column(Float, nullable=False)
    match_mz_error = Column(Float, nullable=False)
    match_isotope_similarity = Column(Float, nullable=False)
    match_score = Column(
        Float, CheckConstraint("match_score BETWEEN 0 AND 1"), nullable=False
    )
    # match_category = Column(Integer, CheckConstraint("match_category BETWEEN 0 AND 2"))
    match_isotope_utc_created = Column(TIMESTAMP)
    match_isotope_utc_modified = Column(TIMESTAMP)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match_isotope")
    target_isotope = relationship("TargetIsotope", back_populates="match_isotope")

    # Define indexes
    __table_args__ = (
        Index("idx_match_isotope_sample_item", "sample_item_id"),
        Index("idx_match_isotope_sample_peak_id", "sample_peak_id"),
    )


class AttributeTemplate(Base):
    __tablename__ = "attribute_template"
    attribute_template_id = Column(String(16), nullable=False, primary_key=True)
    name = Column(String(256), nullable=False)
    type = Column(String(64))
    template = Column(JSON)


class InstrumentFunction(Base):
    __tablename__ = "instrument_function"
    instrument_function_id = Column(String(32), nullable=False, primary_key=True)
    instrument = Column(String(64), nullable=False)
    method_file = Column(String(256), nullable=False)
    datetime_utc = Column(TIMESTAMP, nullable=False)
    peakshape = Column(JSON)
    resolution_function = Column(JSON)

    # Define relationships
    sample_file = relationship("SampleFile", back_populates="instrument_function")


class Sample(Base):
    __tablename__ = "sample_view"
    __table_args__ = {"extend_existing": True}
    # All columns are read-only as this is a view, not a base table

    sample_item_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    sample_file_id: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    instrument_function_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("instrument_function.instrument_function_id", ondelete="SET NULL"),
        nullable=True,
    )
    sample_batch_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("sample_batch.sample_batch_id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_item_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(256), nullable=False)
    instrument: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sample_item_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=False)
    locked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text(f"{sample_item_config.DEFAULT_LOCKED_STATUS}"),
    )
    method_file: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    t0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    t1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_item_attributes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    filter_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    polarity: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    ionization_mode_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey(
            "ionization_mode.ionization_mode_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    range: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    mz_calibration: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    datetime: Mapped[Optional[str]] = mapped_column(TIMESTAMP, nullable=True)
    datetime_utc: Mapped[Optional[str]] = mapped_column(TIMESTAMP, nullable=True)
    sample_item_utc_created: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    sample_item_utc_modified: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP, nullable=True
    )
