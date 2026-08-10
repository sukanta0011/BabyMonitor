from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from ..global_variables import DATABASE_URL


engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool) # NullPool make sure the creation of new session
async_session = async_sessionmaker(bind=engine)


async def get_db():
    async with async_session() as session:
        yield session