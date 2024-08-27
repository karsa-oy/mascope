from sqlalchemy import text

import mascope_runtime as runtime

logger = runtime.logger.service("backend")


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
    logger.debug("Query plan:")
    for row in result.fetchall():
        logger.debug(row)
