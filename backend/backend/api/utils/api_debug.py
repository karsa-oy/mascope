from sqlalchemy import text


async def explain_query_plan(session, query):
    """
    Executes an EXPLAIN QUERY PLAN for the given query and prints the results.

    :param session: The database session.
    :param query: The SQLAlchemy query to explain.
    TODO_debug_mode Debug mode conditional logging of the query plan
    """
    explain_stmt = text(
        f"EXPLAIN QUERY PLAN {query.compile(compile_kwargs={'literal_binds': True})}"
    )
    result = await session.execute(explain_stmt)
    print("EXPLAIN QUERY PLAN:")
    for row in result.fetchall():
        print(row)
