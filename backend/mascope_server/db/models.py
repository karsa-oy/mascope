from datetime import datetime, timezone
from sqlalchemy import (
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
    text,
)

from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql.schema import CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from fastapi_users.db import (
    SQLAlchemyBaseUserTable,
)


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
        TIMESTAMP, default=datetime.now(timezone.utc), nullable=False
    )

    # Define relationships
    role = relationship("Role", back_populates="users")


class Role(Base):
    __tablename__ = "role"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(length=50), unique=True, nullable=False
    )  # Role name (e.g., "admin", "user")
    permissions: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Define relationships
    users = relationship("User", back_populates="role")


class Workspace(Base):
    __tablename__ = "workspace"
    workspace_id = Column(String(16), nullable=False, primary_key=True)
    workspace_name = Column(String(256), nullable=False)
    workspace_description = Column(Text)
    workspace_utc_created = Column(TIMESTAMP)
    workspace_utc_modified = Column(TIMESTAMP)

    # Define relationships
    sample_batch = relationship(
        "SampleBatch", back_populates="workspace", cascade="all, delete, delete-orphan"
    )


class SampleBatch(Base):
    __tablename__ = "sample_batch"
    sample_batch_id = Column(String(16), primary_key=True)
    workspace_id = Column(
        String(16),
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_batch_name = Column(String, nullable=False)
    sample_batch_description = Column(Text)
    build_params = Column(JSON)
    sample_batch_utc_created = Column(TIMESTAMP)
    sample_batch_utc_modified = Column(TIMESTAMP)

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


class SampleItem(Base):
    __tablename__ = "sample_item"
    sample_item_id = Column(String(16), nullable=False, primary_key=True)
    sample_batch_id = Column(
        String(16),
        ForeignKey("sample_batch.sample_batch_id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = Column(String(256), nullable=False)
    sample_item_name = Column(String(256), nullable=False)
    sample_item_type = Column(String(64), nullable=False)
    sample_item_attributes = Column(JSON)
    sample_item_utc_created = Column(TIMESTAMP)
    sample_item_utc_modified = Column(TIMESTAMP)
    filter_id = Column(String(6))

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
    match_interference = relationship(
        "MatchInterference",
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


class SampleFile(Base):
    __tablename__ = "sample_file"
    sample_file_id = Column(String(16), nullable=False, primary_key=True)
    filename = Column(String(256), nullable=False, unique=True)
    instrument = Column(String(64))
    datetime = Column(TIMESTAMP)
    datetime_utc = Column(TIMESTAMP)
    length = Column(Float)
    range = Column(JSON)
    mz_calibration = Column(JSON)
    tic = Column(Float)
    polarity = Column(String(1))

    # Define relationships
    # TODO_db issue #376
    # sample_item = relationship("SampleItem", back_populates="sample_file")


class TargetCollection(Base):
    __tablename__ = "target_collection"
    target_collection_id = Column(String(16), nullable=False, primary_key=True)
    target_collection_name = Column(String(256), nullable=False)
    target_collection_description = Column(Text)
    target_collection_type = Column(
        String(64),
        nullable=False,
        # the default is set at the database level using server_default
        server_default=text("'TARGETS'"),
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
    ionization_mechanism_id = Column(String(16), nullable=False, primary_key=True)
    ionization_mechanism_polarity = Column(String(1), nullable=False)
    ionization_mechanism = Column(String, nullable=False, unique=True)
    reagent = Column(String, nullable=True)

    # Define relationships
    target_ion = relationship(
        "TargetIon",
        back_populates="ionization_mechanism",
        cascade="all, delete, delete-orphan",
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

    # Define relationships
    target_ion = relationship("TargetIon", back_populates="target_isotope")
    match_interference = relationship(
        "MatchInterference",
        back_populates="target_isotope",
        cascade="all, delete, delete-orphan",
    )
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
    sample_peak_area_sum = Column(Float, nullable=False)
    sample_peak_interference_sum = Column(Float, nullable=False)
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
    sample_peak_area_sum = Column(Float, nullable=False)
    sample_peak_interference_sum = Column(Float, nullable=False)
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
    sample_peak_area_sum = Column(Float, nullable=False)
    sample_peak_interference_sum = Column(Float, nullable=False)
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
    sample_peak_area_sum = Column(Float, nullable=False)
    sample_peak_interference_sum = Column(Float, nullable=False)
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


class MatchInterference(Base):
    __tablename__ = "match_interference"
    match_interference_id = Column(String(32), nullable=False, primary_key=True)
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
    sample_peak_interference = Column(Float, nullable=False)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match_interference")
    target_isotope = relationship("TargetIsotope", back_populates="match_interference")

    # Define indexes
    __table_args__ = (Index("idx_match_interference_sample_item", "sample_item_id"),)


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
    sample_peak_id = Column(Integer, nullable=False)
    sample_peak_mz = Column(Float, nullable=False)
    sample_peak_area = Column(Float, nullable=False)
    sample_peak_area_relative = Column(Float, nullable=False)
    sample_peak_tof = Column(Float, nullable=False)
    match_abundance_error = Column(Float, nullable=False)
    match_mz_error = Column(Float, nullable=False)
    match_isotope_correlation = Column(Float, nullable=False)
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
    __table_args__ = (Index("idx_match_isotope_sample_item", "sample_item_id"),)


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
    datetime_utc = Column(TIMESTAMP)
    peakshape = Column(JSON)
    resolution_function = Column(JSON)


class Sample(Base):
    __tablename__ = "sample_view"
    __table_args__ = {"extend_existing": True}
    # All columns are read-only as this is a view, not a base table
    sample_item_id = Column(String(16), primary_key=True)
    sample_file_id = Column(String(16))
    sample_batch_id = Column(String(16), ForeignKey("sample_batch.sample_batch_id"))
    sample_item_name = Column(String(256))
    filename = Column(String(256))
    instrument = Column(String(64))
    sample_item_type = Column(String(64))
    sample_item_attributes = Column(JSON)
    filter_id = Column(String(6))
    length = Column(Float)
    tic = Column(Float)
    polarity = Column(String(1))
    range = Column(JSON)
    mz_calibration = Column(JSON)
    datetime = Column(TIMESTAMP)
    datetime_utc = Column(TIMESTAMP)
    sample_item_utc_created = Column(TIMESTAMP)
    sample_item_utc_modified = Column(TIMESTAMP)
