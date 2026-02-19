"""
Api debugging utilities.
"""

from sqlalchemy import text

from mascope_backend.runtime import runtime


async def explain_query_plan(session, query):
    """
    Executes an EXPLAIN QUERY PLAN (SQLite) or EXPLAIN (PostgreSQL) for the given query.

    :param session: The database session.
    :param query: The SQLAlchemy query to explain.
    """
    compiled = query.compile(compile_kwargs={"literal_binds": True})

    if runtime.config.database.type == "sqlite":
        explain_sql = f"EXPLAIN QUERY PLAN {compiled}"
    else:
        explain_sql = f"EXPLAIN {compiled}"

    result = await session.execute(text(explain_sql))
    runtime.logger.debug("Query plan:")
    for row in result.fetchall():
        runtime.logger.debug(row)
