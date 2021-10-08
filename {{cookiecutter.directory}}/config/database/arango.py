# Arango

def init_database(registry):

    from reha.arango import Database
    from reiter.arango.connector import Connector

    database = Database(
        Connector.from_config(
            user="ck",
            password="ck",
            database="p2",
            url="http://127.0.0.1:8529"
        )
    )

    database.instanciate({
        "users": registry['user'],
        "files": registry['file'],
        "documents": registry['document']
    })

    return database
