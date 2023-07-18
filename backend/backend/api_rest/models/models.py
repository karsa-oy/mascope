from sqlalchemy import (
    TIMESTAMP,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import CheckConstraint
from sqlalchemy.ext.declarative import declarative_base


class BaseMixin(object):
    def to_dict(self, include_tic=False, include_intensity=False, compounds=None):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if include_tic and hasattr(self, "tic"):
            data["tic"] = self.tic
        if include_intensity and compounds:
            compounds = compounds.split(",")
            compounds_intensity = {}
            for compound in compounds:
                compounds_intensity[compound] = getattr(self, compound, 0)
            data["compounds_intensity"] = compounds_intensity
        return data


Base = declarative_base(cls=BaseMixin)


class Workspace(Base):
    __tablename__ = "workspace"
    workspace_id = Column(String, primary_key=True)
    workspace_name = Column(String)
    workspace_description = Column(Text)
    workspace_utc_created = Column(TIMESTAMP)
    workspace_utc_modified = Column(TIMESTAMP)

    # Define relationships
    sample_batch = relationship("SampleBatch", back_populates="workspace")


class SampleBatch(Base):
    __tablename__ = "sample_batch"
    sample_batch_id = Column(String, primary_key=True)
    workspace_id = Column(String, ForeignKey("workspace.workspace_id"))
    sample_batch_name = Column(String)
    sample_batch_description = Column(Text)
    build_params = Column(JSON)
    filter_params = Column(JSON)
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
    sample_item_id = Column(String, primary_key=True)
    sample_batch_id = Column(String, ForeignKey("sample_batch.sample_batch_id"))
    filename = Column(String, ForeignKey("sample_file.filename"))
    sample_item_name = Column(String)
    sample_item_type = Column(String)
    sample_item_attributes = Column(String)
    sample_item_utc_created = Column(TIMESTAMP)
    sample_item_utc_modified = Column(TIMESTAMP)
    filter_id = Column(String)

    # Define relationships
    sample_batch = relationship("SampleBatch", back_populates="sample_item")
    sample_file = relationship(
        "SampleFile", back_populates="sample_item", foreign_keys=[filename]
    )
    match = relationship(
        "Match", back_populates="sample_item", cascade="all, delete, delete-orphan"
    )
    match_interference = relationship(
        "MatchInterference",
        back_populates="sample_item",
        cascade="all, delete, delete-orphan",
    )

    # Methods
    async def get_compound_intensity(self, session, compounds):
        sql = f"""
            SELECT
                target_compound_formula,
                IFNULL(SUM(sample_peak_area_sum), 0) AS intensity
            FROM (
                SELECT
                    sample_item_id,
                    target_compound_formula,
                    target_compound_id,
                    SUM(sample_peak_area) AS sample_peak_area_sum
                FROM
                    match
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN target_ion
                    NATURAL LEFT JOIN target_compound
                WHERE (
                    sample_item_id = :sample_item_id
                    AND target_compound_formula IN ({','.join(f':param_{i}' for i in range(len(compounds)))})
                )
                GROUP BY target_compound_id, target_ion_id
            )
            GROUP BY target_compound_id;
            """

        # Bind the parameters
        params = {
            "sample_item_id": self.sample_item_id,
            **{f"param_{i}": compound for i, compound in enumerate(compounds)},
        }

        result = await session.execute(text(sql), params)

        # Store the results in the SampleItem object
        for row in result:
            setattr(self, row[0], row[1])


class SampleFile(Base):
    __tablename__ = "sample_file"
    sample_file_id = Column(String(256), primary_key=True)
    filename = Column(String(256), nullable=False, unique=True)
    instrument = Column(String(64))
    datetime = Column(TIMESTAMP)
    datetime_utc = Column(TIMESTAMP)
    length = Column(Float)
    range = Column(JSON)
    mz_calibration = Column(JSON)
    tic = Column(Float)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="sample_file")


class Match(Base):
    __tablename__ = "match"
    match_id = Column(String, primary_key=True)
    target_isotope_id = Column(String, ForeignKey("target_isotope.target_isotope_id"))
    sample_item_id = Column(String, ForeignKey("sample_item.sample_item_id"))
    sample_peak_id = Column(Integer)
    sample_peak_mz = Column(Float)
    sample_peak_area = Column(Float)
    sample_peak_area_relative = Column(Float)
    sample_peak_tof = Column(Float)
    match_abundance_error = Column(Float)
    match_mz_error = Column(Float)
    match_score = Column(Float)
    match_isotope_correlation = Column(Float)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match")
    target_isotope = relationship("TargetIsotope", back_populates="match")


class TargetCollectionInSampleBatch(Base):
    __tablename__ = "target_collection_in_sample_batch"
    target_collection_id = Column(
        String(16),
        ForeignKey("target_collection.target_collection_id"),
        primary_key=True,
    )
    sample_batch_id = Column(
        String(16), ForeignKey("sample_batch.sample_batch_id"), primary_key=True
    )

    # Define relationships
    target_collection = relationship("TargetCollection", back_populates="sample_batch")
    sample_batch = relationship("SampleBatch", back_populates="target_collection")


class TargetCollection(Base):
    __tablename__ = "target_collection"
    target_collection_id = Column(String(16), primary_key=True)
    target_collection_name = Column(String(256))
    target_collection_description = Column(Text)

    # Define relationships
    sample_batch = relationship(
        "TargetCollectionInSampleBatch", back_populates="target_collection"
    )
    target_compound = relationship(
        "TargetCompoundInTargetCollection",
        back_populates="target_collection",
    )


class TargetCompoundInTargetCollection(Base):
    __tablename__ = "target_compound_in_target_collection"
    target_compound_id = Column(
        String(32), ForeignKey("target_compound.target_compound_id"), primary_key=True
    )
    target_collection_id = Column(
        String(16),
        ForeignKey("target_collection.target_collection_id"),
        primary_key=True,
    )

    # Define relationships
    target_collection = relationship(
        "TargetCollection", back_populates="target_compound"
    )
    target_compound = relationship("TargetCompound", back_populates="target_collection")


class TargetCompound(Base):
    __tablename__ = "target_compound"
    target_compound_id = Column(String, primary_key=True)
    target_compound_name = Column(Text)
    target_compound_formula = Column(String)
    cas_number = Column(String(12))

    # Define relationships
    target_collection = relationship(
        "TargetCompoundInTargetCollection",
        back_populates="target_compound",
    )
    target_ion = relationship(
        "TargetIon",
        back_populates="target_compound",
    )


class TargetIon(Base):
    __tablename__ = "target_ion"
    target_ion_id = Column(String, primary_key=True)
    target_compound_id = Column(
        String, ForeignKey("target_compound.target_compound_id")
    )
    ionization_mechanism_id = Column(
        String, ForeignKey("ionization_mechanism.ionization_mechanism_id")
    )
    target_ion_formula = Column(String)

    # Define relationships
    target_compound = relationship(
        "TargetCompound",
        back_populates="target_ion",
    )
    ionization_mechanism = relationship(
        "IonizationMechanism", back_populates="target_ion"
    )
    target_isotope = relationship("TargetIsotope", back_populates="target_ion")


class IonizationMechanism(Base):
    __tablename__ = "ionization_mechanism"
    ionization_mechanism_id = Column(String(16), primary_key=True)
    ionization_mechanism_polarity = Column(String(1))
    ionization_mechanism = Column(String)
    reagent = Column(String)

    # Define relationships
    target_ion = relationship("TargetIon", back_populates="ionization_mechanism")


class TargetIsotope(Base):
    __tablename__ = "target_isotope"
    target_isotope_id = Column(String, primary_key=True)
    target_ion_id = Column(String, ForeignKey("target_ion.target_ion_id"))
    mz = Column(Float)
    relative_abundance = Column(
        Float, CheckConstraint("relative_abundance >= 0 AND relative_abundance <= 1")
    )
    # Define relationships
    target_ion = relationship("TargetIon", back_populates="target_isotope")
    match_interference = relationship(
        "MatchInterference", back_populates="target_isotope"
    )
    match = relationship(
        "Match",
        back_populates="target_isotope",
    )


class MatchInterference(Base):
    __tablename__ = "match_interference"
    match_interference_id = Column(String(32), primary_key=True)
    target_isotope_id = Column(
        String(32), ForeignKey("target_isotope.target_isotope_id"), nullable=False
    )
    sample_item_id = Column(
        String(16), ForeignKey("sample_item.sample_item_id"), nullable=False
    )
    sample_peak_interference = Column(Float, nullable=False)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="match_interference")
    target_isotope = relationship("TargetIsotope", back_populates="match_interference")


class AttributeTemplate(Base):
    __tablename__ = "attribute_template"
    attribute_template_id = Column(String(256), primary_key=True)
    name = Column(String(256), nullable=False)
    type = Column(String(64))
    template = Column(JSON)


class InstrumentFunction(Base):
    __tablename__ = "instrument_function"
    instrument_function_id = Column(String(32), primary_key=True)
    instrument = Column(String(64))
    datetime_utc = Column(TIMESTAMP)
    peakshape = Column(JSON)
    resolution_function = Column(JSON)


class Sample(Base):
    __tablename__ = "sample_view"
    __table_args__ = {"extend_existing": True}

    # all columns read-only
    sample_item_id = Column(String, primary_key=True)
    sample_file_id = Column(String)
    sample_batch_id = Column(String)
    sample_item_name = Column(String)
    filename = Column(String)
    instrument = Column(String)
    sample_item_type = Column(String)
    sample_item_attributes = Column(String)
    filter_id = Column(String)
    length = Column(Float)
    tic = Column(Float)
    range = Column(JSON)
    mz_calibration = Column(JSON)
    datetime = Column(TIMESTAMP)
    datetime_utc = Column(TIMESTAMP)
    sample_item_utc_created = Column(TIMESTAMP)
    sample_item_utc_modified = Column(TIMESTAMP)
