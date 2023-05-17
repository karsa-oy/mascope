from sqlalchemy import TIMESTAMP, Column, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


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


class SampleBatch(Base):
    __tablename__ = "sample_batch"
    sample_batch_id = Column(String, primary_key=True)
    workspace_id = Column(String, ForeignKey("workspace.workspace_id"))
    sample_batch_name = Column(String)
    sample_batch_description = Column(Text)
    build_params = Column(String)
    filter_params = Column(String)
    sample_batch_utc_created = Column(TIMESTAMP)
    sample_batch_utc_modified = Column(TIMESTAMP)

    # Define relationships
    sample_item = relationship("SampleItem", back_populates="sample_batch")


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
    matches = relationship("Match", back_populates="sample_item")

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
    sample_file_id = Column(String, primary_key=True)
    filename = Column(String, unique=True)
    #     instrument = Column(String)
    #     datetime = Column(TIMESTAMP)
    #     datetime_utc = Column(TIMESTAMP)
    #     length = Column(Float)
    #     range = Column(String)
    #     mz_calibration = Column(String)
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
    sample_item = relationship("SampleItem", back_populates="matches")
    # target_isotope = relationship("TargetIsotope", back_populates="matches")


class TargetIsotope(Base):
    __tablename__ = "target_isotope"
    target_isotope_id = Column(String, primary_key=True)
    target_ion_id = Column(String, ForeignKey("target_ion.target_ion_id"))
    # mz = Column(Float)
    # relative_abundance = Column(Float)


class TargetIon(Base):
    __tablename__ = "target_ion"
    target_ion_id = Column(String, primary_key=True)
    target_compound_id = Column(
        String, ForeignKey("target_compound.target_compound_id")
    )
    # ionization_mechanism_id = Column(
    #     String, ForeignKey("ionization_mechanism.ionization_mechanism_id")
    # )
    # target_ion_formula = Column(String)


class TargetCompound(Base):
    __tablename__ = "target_compound"
    target_compound_id = Column(String, primary_key=True)
    #     target_compound_name = Column(Text)
    target_compound_formula = Column(String)
