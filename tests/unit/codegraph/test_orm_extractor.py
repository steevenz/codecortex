"""
Tests for ORM dataflow analysis.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.modules.codegraph.core.orm import ORMExtractor, extract_orm_from_files


def test_sqlalchemy_model():
    extractor = ORMExtractor()
    content = """
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
"""
    models = extractor.extract_models_from_file(content, "models.py", "python")
    assert len(models) >= 1
    assert models[0].name == "User"
    assert models[0].table == "users"


def test_django_model():
    extractor = ORMExtractor()
    content = """
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
"""
    models = extractor.extract_models_from_file(content, "models.py", "python")
    assert len(models) >= 1
    assert models[0].name == "Product"
    assert len(models[0].fields) > 0


def test_prisma_model():
    extractor = ORMExtractor()
    content = """
model User {
    id        Int      @id @default(autoincrement())
    email     String   @unique
    name      String?
    posts     Post[]
}
"""
    models = extractor.extract_models_from_file(content, "schema.prisma", "prisma")
    assert len(models) == 1
    assert models[0].name == "User"
    assert len(models[0].fields) >= 3


def test_sqlalchemy_query():
    extractor = ORMExtractor()
    content = """
users = session.query(User).filter(User.name == "Alice").all()
user = db.query(User).get(1)
"""
    queries = extractor.extract_queries_from_file(content, "queries.py", "python")
    assert len(queries) >= 2
    assert all(q.model == "User" for q in queries)


def test_django_query():
    extractor = ORMExtractor()
    content = """
users = User.objects.filter(is_active=True)
user = User.objects.get(id=1)
User.objects.create(name="Alice")
"""
    queries = extractor.extract_queries_from_file(content, "views.py", "python")
    assert len(queries) >= 3


def test_extract_orm_from_files():
    files = [
        {"path": "models.py", "content": "from sqlalchemy.orm import DeclarativeBase\n\nclass Base(DeclarativeBase):\n    pass\n\nclass User(Base):\n    __tablename__ = 'users'\n    id = Column(Integer, primary_key=True)\n", "language": "python"},
    ]
    result = extract_orm_from_files(files)
    assert result["model_count"] >= 1


if __name__ == "__main__":
    test_sqlalchemy_model()
    test_django_model()
    test_prisma_model()
    test_sqlalchemy_query()
    test_django_query()
    test_extract_orm_from_files()
    print("All ORM dataflow tests passed.")
