# SQL engine

def init_database(registry):
    import importscan
    import reha.sql
    from roughrider.sqlalchemy.component import SQLAlchemyEngine

    database = reha.sql.Database(
        SQLAlchemyEngine.from_url(
            name="sql",
            url="sqlite:///example.db"
        )
    )
    importscan.scan(reha.sql)
    database.instanciate(registry)
    return database
