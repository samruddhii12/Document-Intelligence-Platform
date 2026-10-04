from backend.database import Base,engine
import backend.models.db_models  # noqa
if __name__=="__main__":
    Base.metadata.create_all(engine)
    print("Database schema created.")
