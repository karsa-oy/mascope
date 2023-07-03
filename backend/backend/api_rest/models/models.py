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
    case,
    and_,
    func,
    select,
)
from sqlalchemy.orm import relationship, column_property, backref
from sqlalchemy.sql.schema import CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property


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
        # TODO add cascade deletes when editting DELETE sample_item
        # cascade="all, delete, delete-orphan",
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

    # # Define relationships
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


# class Sample(Base):
#     # No __tablename__ since this is a composite model not backed by a specific table

#     # Primary Key
#     sample_id = Column(
#         String, primary_key=True
#     )  # Ensure this uniquely identifies a Sample

#     # Foreign Keys - Not required unless you have a specific use case
#     # sample_item_id = Column(String, ForeignKey("sample_item.sample_item_id"))
#     # filename = Column(String, ForeignKey("sample_file.filename"))

#     # Relationships - Link to SampleItem and SampleFile
#     sample_item = relationship("SampleItem", back_populates="sample")
#     sample_file = relationship("SampleFile", back_populates="sample")

#     # Composite properties
#     @hybrid_property
#     def sample_item_name(self):
#         return self.sample_item.sample_item_name

#     @hybrid_property
#     def filename(self):
#         return self.sample_file.filename

#     # ... add more fields as necessary


# ______________________________________________________________________
# class Sample(Base):
#     __tablename__ = "sample"

#     # Primary Key
#     sample_id = Column(String, primary_key=True)

#     # Relationships
#     sample_item = relationship("SampleItem", back_populates="sample", uselist=False)
#     sample_file = relationship("SampleFile", back_populates="sample", uselist=False)
#     # target_compound = relationship("TargetCompound")
#     # target_ion = relationship("TargetIon")
#     # target_isotope = relationship("TargetIsotope")
#     # match = relationship("Match", back_populates="sample")
#     # match_interferences = relationship("MatchInterference", back_populates="sample")

#     # Foreign Keys
#     sample_item_id = Column(String, ForeignKey("sample_item.sample_item_id"))
#     filename = Column(String, ForeignKey("sample_file.filename"))
#     # target_compound_id = Column(String, ForeignKey("target_compound.target_compound_id"))
#     # target_ion_id = Column(String, ForeignKey("target_ion.target_ion_id"))
#     # target_isotope_id = Column(String, ForeignKey("target_isotope.target_isotope_id"))

#     # Columns
#     # sample_item_name = Column(String)
#     # sample_item_type = Column(String)
#     # target_compound_formula = Column(String)
#     # target_compound_name = Column(String)
#     # target_ion_formula = Column(String)
#     # target_ion_mechanism = Column(String)

#     # sample_peak_interference = column_property(
#     #     select([MatchInterference.__table__.c.sample_peak_interference]).where(
#     #         MatchInterference.sample_item_id == sample_item_id
#     #     )
#     # )
#     # sample_peak_interference = column_property(
#     #     select([MatchInterference.sample_peak_interference]).where(
#     #         MatchInterference.sample_item_id == sample_item_id
#     #     )
#     # )

#     # The following properties can be used to emulate batch_match_filter

#     # @hybrid_property
#     # def sample_peak_area(self):
#     #     # Emulates the logic inside the CASE WHEN statement
#     #     return self.match.sample_peak_area if self._match_filter_condition() else 0

#     # @hybrid_property
#     # def match_score(self):
#     #     # Emulates the logic inside the CASE WHEN statement
#     #     return self.match.match_score if self._match_filter_condition() else 0

#     # def _match_filter_condition(
#     #     self,
#     #     mz_tolerance,
#     #     isotope_ratio_tolerance,
#     #     min_isotope_correlation,
#     #     min_isotope_abundance,
#     #     peak_min_intensity,
#     # ):
#     #     # This private method is used to encapsulate the filter condition used in the CASE WHEN statements
#     #     return (
#     #         abs(self.match.match_mz_error) <= mz_tolerance
#     #         and abs(self.match.match_abundance_error) <= isotope_ratio_tolerance
#     #         and max(self.match.match_isotope_correlation, 0) >= min_isotope_correlation
#     #         and self.match.sample_peak_area >= peak_min_intensity
#     #         and self.match.relative_abundance >= min_isotope_abundance
#     #     )


# ________________________________________________________________________

# class Sample(Base):
#     __tablename__ = "sample"

#     # SampleItem properties
#     sample_item_id = Column(String, primary_key=True)
#     sample_batch_id = Column(String, ForeignKey("sample_batch.sample_batch_id"))
#     filename = Column(String, ForeignKey("sample_file.filename"))
#     sample_item_name = Column(String)
#     sample_item_type = Column(String)
#     sample_item_attributes = Column(String)
#     sample_item_utc_created = Column(TIMESTAMP)
#     sample_item_utc_modified = Column(TIMESTAMP)
#     filter_id = Column(String)

#     # SampleFile properties
#     instrument = Column(String(64))
#     datetime = Column(TIMESTAMP)
#     datetime_utc = Column(TIMESTAMP)
#     length = Column(Float)
#     range = Column(JSON)
#     mz_calibration = Column(JSON)
#     tic = Column(Float)

#     # Match properties
#     match_score = Column(Float)
#     match_abundance_error = Column(Float)
#     match_mz_error = Column(Float)
#     match_isotope_correlation = Column(Float)
#     sample_peak_area = Column(Float)

#     # MatchInterference properties
#     sample_peak_interference = Column(Float)

#     # TargetIsotope properties
#     relative_abundance = Column(Float)

#     # TargetIon properties
#     target_ion_formula = Column(String)

#     # IonizationMechanism properties
#     ionization_mechanism = Column(String)

#     # TargetCompound properties
#     target_compound_formula = Column(String)
#     target_compound_id = Column(String)
#     target_compound_name = Column(String)

#     # More properties to aggregate data
#     # e.g., MAX(match_score) AS match_score
#     match_score = column_property(
#         select([
#             func.max(Match.match_score)
#         ]).where(
#             and_(
#                 Match.sample_item_id == sample_item_id,
#                 Match.match_mz_error <= ${mzTolerance},
#                 Match.match_abundance_error <= ${isotopeRatioTolerance},
#                 Match.match_isotope_correlation >= ${minIsotopeCorrelation},
#                 TargetIsotope.relative_abundance >= ${minIsotopeAbundance},
#                 Match.sample_peak_area >= ${peakMinIntensity}
#             )
#         )
#     )

#     sample_peak_area_sum = column_property(
#         select([
#             func.sum(Match.sample_peak_area)
#         ]).where(
#             and_(
#                 Match.sample_item_id == sample_item_id,
#                 Match.match_mz_error <= ${mzTolerance},
#                 Match.match_abundance_error <= ${isotopeRatioTolerance},
#                 Match.match_isotope_correlation >= ${minIsotopeCorrelation},
#                 TargetIsotope.relative_abundance >= ${minIsotopeAbundance},
#                 Match.sample_peak_area >= ${peakMinIntensity}
#             )
#         )
#     )

#     # Similar property definitions for other aggregated fields...

#     # Define relationships
