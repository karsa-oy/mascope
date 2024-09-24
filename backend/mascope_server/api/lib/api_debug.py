from sqlalchemy import text

from mascope_server.runtime import runtime


async def explain_query_plan(session, query):
    """
    Executes an EXPLAIN QUERY PLAN for the given query and prints the results.

    :param session: The database session.
    :param query: The SQLAlchemy query to explain.
    """
    explain_stmt = text(
        f"EXPLAIN QUERY PLAN {query.compile(compile_kwargs={'literal_binds': True})}"
    )
    result = await session.execute(explain_stmt)
    runtime.logger.debug("Query plan:")
    for row in result.fetchall():
        runtime.logger.debug(row)
