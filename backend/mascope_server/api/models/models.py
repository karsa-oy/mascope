from sqlalchemy import (
    TIMESTAMP,
    Column,
    Index,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import CheckConstraint
from sqlalchemy.ext.declarative import declarative_base


class BaseMixin(object):
    def to_dict(
        self,
        include_tic=False,
        include_intensity=False,
        compounds=None,
        include_selection=False,
    ):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if include_tic and hasattr(self, "tic"):
            data["tic"] = self.tic
        if include_intensity and compounds:
            compounds = compounds.split(",")
            compounds_intensity = {}
            for compound in compounds:
                compounds_intensity[compound] = getattr(self, compound, 0)
            data["compounds_intensity"] = compounds_intensity
        if include_selection:
            data["selection"] = 0
        return data


Base = declarative_base(cls=BaseMixin)


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
    match = relationship(
        "Match", back_populates="sample_item", cascade="all, delete, delete-orphan"
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
    target_collection_type = Column(String(64), nullable=False, default="TARGETS")

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
        ForeignKey("ionization_mechanism.ionization_mechanism_id", ondelete="CASCADE"),
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
    ionization_mechanism_polarity = Column(
        String(1),
        nullable=False,
    )
    ionization_mechanism = Column(String)
    reagent = Column(String)

    # Define relationships
    target_ion = relationship("TargetIon", back_populates="ionization_mechanism")


class TargetIsotope(Base):
    __tablename__ = "target_isotope"
    target_isotope_id = Column(String(16), nullable=False, primary_key=True)
    target_ion_id = Column(
        String(16),
        ForeignKey("target_ion.target_ion_id", ondelete="CASCADE"),
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
    match = relationship(
        "Match",
        back_populates="target_isotope",
        cascade="all, delete, delete-orphan",
    )


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


class Match(Base):
    __tablename__ = "match"
    match_id = Column(String(32), nullable=False, primary_key=True)
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
    match_score = Column(
        Float, CheckConstraint("match_score BETWEEN 0 AND 1"), nullable=False
    )
    match_isotope_correlation = Column(Float, nullable=False)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match")
    target_isotope = relationship("TargetIsotope", back_populates="match")

    # Define indexes
    __table_args__ = (Index("idx_match_sample_item", "sample_item_id"),)


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
