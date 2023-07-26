import pandas as pd

from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select, or_
from typing import List

from backend.db.conn import conn
from backend.db.id import gen_id
from backend.lib.molmass import Formula
from backend.db_api_rest import async_session

from .ionization_mechanisms_controller import get_ionization_mechanisms
from ..models.models import TargetCompound
from ..models.pydantic_models.target_compound_pydantic_model import TargetCompoundBase
from ..models.pydantic_models.target_ion_pydantic_model import TargetIonBase
from ..models.pydantic_models.target_isotope_pydantic_model import TargetIsotopeBase


async def get_target_compounds(
    target_compound_name: str,
    target_compound_formula: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(TargetCompound)

        if target_compound_name:
            stmt = stmt.filter(
                TargetCompound.target_compound_name == target_compound_name
            )

        if target_compound_formula:
            stmt = stmt.filter(
                TargetCompound.target_compound_formula == target_compound_formula
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetCompound, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetCompound, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_compounds = result.scalars().all()

        return {
            "results": total,
            "data": [target_compound.to_dict() for target_compound in target_compounds],
        }


async def get_target_compound_by_id(target_compound_id: str):
    async with async_session() as session:
        stmt = select(TargetCompound).filter(
            TargetCompound.target_compound_id == target_compound_id
        )
        result = await session.execute(stmt)
        target_compound = result.scalars().first()

        if not target_compound:
            raise HTTPException(
                status_code=404,
                detail=f"TargetCompound with ID {target_compound_id} not found",
            )

        return target_compound.to_dict()


async def delete_target_compound(target_compound_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(TargetCompound).filter(
                TargetCompound.target_compound_id == target_compound_id
            )
        )
        target_compound = result.scalar_one_or_none()
        if not target_compound:
            raise HTTPException(status_code=404, detail="Target compound not found")

        await session.delete(target_compound)
        await session.commit()


async def create_target_compound(target_compounds: List[TargetCompoundBase]):
    # helper functions
    def norm(name, lower=False):
        if lower:
            name = name.lower()
        return " ".join(name.strip().split())

    def charge_string(raw_ion):
        if raw_ion.charge == -1:
            charge_string = "-"
        elif raw_ion.charge == +1:
            charge_string = "+"
        else:
            charge_string = ""
        return charge_string

    def generate_target_ions_from_composition():
        # generate and create ion records
        for ionization_mechanism in ionization_mechanisms:
            mechanism = ionization_mechanism["ionization_mechanism"]
            try:
                # get and save ions
                raw_ion = Formula(
                    "("
                    + target_compound.target_compound_formula.rstrip()
                    + mechanism[:-1]
                    + ")"
                    + mechanism[-1]
                )
            except ValueError as e:
                print("Failed to parse ion formula: %s" % e)
            else:
                # construct and save ion row
                ion = TargetIonBase(
                    target_ion_id=gen_id(),
                    target_compound_id=target_compound.target_compound_id,
                    ionization_mechanism_id=ionization_mechanism[
                        "ionization_mechanism_id"
                    ],
                    target_ion_formula=raw_ion.formula + charge_string(raw_ion),
                )

                nonlocal target_ions
                target_ions.append(ion)

                # construct and save isotope rows
                raw_isotopes = raw_ion.mz_spectrum().values()
                nonlocal target_isotopes
                target_isotopes += [
                    TargetIsotopeBase(
                        target_isotope_id=gen_id(),
                        target_ion_id=ion.target_ion_id,
                        mz=mz,
                        relative_abundance=rel_abu,
                    )
                    for [mz, rel_abu] in raw_isotopes
                ]

    def generate_target_ions_from_mass(target_compound_mass):
        # generate and create ion records
        for ionization_mechanism in ionization_mechanisms:
            mechanism = ionization_mechanism["ionization_mechanism"]
            # construct and save ion row
            ion = TargetIonBase(
                target_ion_id=gen_id(),
                target_compound_id=target_compound.target_compound_id,
                ionization_mechanism_id=ionization_mechanism["ionization_mechanism_id"],
                target_ion_formula=(f"{target_compound_mass:.4f}" + mechanism),
            )

            nonlocal target_ions
            target_ions.append(ion)
            # construct and save isotope rows
            raw_ion = Formula("(" + mechanism[1:-1] + ")" + mechanism[-1])
            is_adduct = mechanism[0] == "+"
            if is_adduct:
                raw_isotopes = raw_ion.mz_spectrum().values()
            else:
                raw_isotopes = [(-raw_ion.mz, 1.0)]
            nonlocal target_isotopes
            target_isotopes += [
                TargetIsotopeBase(
                    target_isotope_id=gen_id(),
                    target_ion_id=ion.target_ion_id,
                    mz=(target_compound_mass + reagent_mz),
                    relative_abundance=reagent_rel_abu,
                )
                for [reagent_mz, reagent_rel_abu] in raw_isotopes
            ]

    async with async_session() as session:
        # Fetch ionization mechanisms
        ionization_mechanisms_data = await get_ionization_mechanisms()
        ionization_mechanisms = ionization_mechanisms_data["data"]

        # initialize list of targets to return
        target_compound_ids = []
        # initalized lists of targets to create
        target_compounds_to_create = []
        target_ions = []
        target_isotopes = []

        for target_compound in target_compounds:
            # check if the compound record is already in the database
            existing_compounds = await session.execute(
                select(TargetCompound).filter(
                    or_(
                        func.lower(TargetCompound.target_compound_formula)
                        == norm(target_compound.target_compound_formula, lower=True),
                        TargetCompound.target_compound_formula
                        == norm(target_compound.target_compound_formula, lower=True),
                    )
                )
            )
            existing_compounds = existing_compounds.scalars().all()

            if len(existing_compounds) == 0:
                # save the new compound for creation if it doesn't exist
                target_compound = TargetCompoundBase(
                    target_compound_id=gen_id(),
                    target_compound_name=target_compound.target_compound_name,
                    target_compound_formula=norm(
                        target_compound.target_compound_formula
                    ),
                    cas_number=target_compound.cas_number,
                )

                target_compounds_to_create.append(target_compound)
                target_compound_ids.append(target_compound.target_compound_id)
            elif len(existing_compounds) == 1:
                # use the existing compound record if it does exist
                target_compound = existing_compounds[0]
                target_compound_ids.append(target_compound.target_compound_id)
                continue  # as ions & isotopes are already there in this case
            else:
                # the database is inconsistent
                raise RuntimeError("Duplicate target compound in database")

            try:
                # Target compound given by mass
                target_compound_mass = float(target_compound.target_compound_formula)
                generate_target_ions_from_mass(target_compound_mass)
            except ValueError:
                # Target compound given by composition
                generate_target_ions_from_composition()

        # Convert the targets to DataFrame using their dictionaries
        target_compound_df = pd.DataFrame.from_records(
            [t.dict() for t in target_compounds_to_create]
        )
        target_ion_df = pd.DataFrame.from_records([i.dict() for i in target_ions])
        target_isotope_df = pd.DataFrame.from_records(
            [i.dict() for i in target_isotopes]
        )

        # create the targets
        target_compound_df.to_sql(
            "target_compound", conn, if_exists="append", index=False
        )
        target_ion_df.to_sql("target_ion", conn, if_exists="append", index=False)
        target_isotope_df.to_sql(
            "target_isotope", conn, if_exists="append", index=False
        )
    return target_compound_ids
