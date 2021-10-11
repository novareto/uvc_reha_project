# SQL engine

def init_database(registry):
    import importscan
    import reha.sql

    database = reha.sql.Database.from_url(
    ┆   url="sqlite:///example.db"
    )
    importscan.scan(reha.sql)
    database.instanciate()
    return database
