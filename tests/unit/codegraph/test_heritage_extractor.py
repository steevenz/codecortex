"""
Tests for heritage extraction (class hierarchy).
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.modules.codegraph.core.heritage import HeritageExtractor


def test_python_inheritance():
    extractor = HeritageExtractor()
    content = """
class Animal:
    pass

class Dog(Animal):
    pass

class Puppy(Dog):
    pass
"""
    extractor.extract_from_file(content, "animals.py", "python")
    assert "Animal" in extractor.heritage_map
    assert "Dog" in extractor.heritage_map
    assert "Puppy" in extractor.heritage_map
    assert extractor.heritage_map["Dog"].parent == "Animal"
    assert extractor.heritage_map["Puppy"].parent == "Dog"


def test_python_multiple_inheritance():
    extractor = HeritageExtractor()
    content = """
class A:
    pass

class B(A):
    pass

class C(A):
    pass
"""
    extractor.extract_from_file(content, "multi.py", "python")
    descendants = extractor.get_descendants("A")
    assert "B" in descendants
    assert "C" in descendants


def test_ancestors():
    extractor = HeritageExtractor()
    content = """
class GrandParent: pass
class Parent(GrandParent): pass
class Child(Parent): pass
"""
    extractor.extract_from_file(content, "chain.py", "python")
    ancestors = extractor.get_ancestors("Child")
    assert ancestors == ["Parent", "GrandParent"]


def test_typescript_inheritance():
    extractor = HeritageExtractor()
    content = """
class Animal { }
class Dog extends Animal { }
class Puppy extends Dog implements IBarkable { }
"""
    extractor.extract_from_file(content, "animals.ts", "typescript")
    assert "Dog" in extractor.heritage_map
    assert extractor.heritage_map["Dog"].parent == "Animal"
    assert "IBarkable" in extractor.heritage_map["Puppy"].interfaces


def test_build_hierarchy():
    extractor = HeritageExtractor()
    content = """class A: pass\nclass B(A): pass\nclass C(B): pass\n"""
    extractor.extract_from_file(content, "test.py", "python")
    hierarchy = extractor.build_hierarchy()
    assert "A" in hierarchy
    assert "B" in hierarchy
    assert "C" not in hierarchy  # C has no children


if __name__ == "__main__":
    test_python_inheritance()
    test_python_multiple_inheritance()
    test_ancestors()
    test_typescript_inheritance()
    test_build_hierarchy()
    print("All heritage extraction tests passed.")
