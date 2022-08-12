def load_json_field(json_field):
    # this is insecure and used with duckdb due to
    # an issue that breaks JSON round trip in duckdb:
    # https://github.com/duckdb/duckdb/issues/4303
    return eval(json_field)
