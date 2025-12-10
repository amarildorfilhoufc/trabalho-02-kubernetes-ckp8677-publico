from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from config import Base

class Revista(Base):
    __tablename__ = "revistas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)

    artigos = relationship("Artigo", back_populates="revista", cascade="all, delete-orphan")


class Artigo(Base):
    __tablename__ = "artigos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    autor = Column(String, nullable=True)
    resumo = Column(String, nullable=True)

    revista_id = Column(Integer, ForeignKey("revistas.id"))
    revista = relationship("Revista", back_populates="artigos")

