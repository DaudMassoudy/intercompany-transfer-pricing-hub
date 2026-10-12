from sqlalchemy.orm import declarative_base

# Declarative metadata is kept separate from engine creation so migration
# tooling can generate offline SQL without importing a DBAPI driver.
Base = declarative_base()
