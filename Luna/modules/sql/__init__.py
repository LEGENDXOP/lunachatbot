from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

DB_URI = "postgres://uf9l14m48joo5t:p531afe291cdbdce458b5f25029999ff9f41b3bbfbe29a5f95d942af06ab65142@ec2-52-86-70-101.compute-1.amazonaws.com:5432/dac23n77lo9u89"


def start() -> scoped_session:
    engine = create_engine(DB_URI, client_encoding="utf8")
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


BASE = declarative_base()
SESSION = start()

