"""
Api debugging utilities.
"""

from sqlalchemy import text

from mascope_backend.runtime import runtime


async def explain_query_plan(session, query):
    """
    Executes an EXPLAIN (PostgreSQL) for the given query.

    :param session: The database session.
    :param query: The SQLAlchemy query to explain.
    """
    compiled = query.compile(compile_kwargs={"literal_binds": True})
    result = await session.execute(text(f"EXPLAIN {compiled}"))
    runtime.logger.debug("Query plan:")
    for row in result.fetchall():
        runtime.logger.debug(row)
