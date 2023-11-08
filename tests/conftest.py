"""Dummy conftest.py for glass

Read more about conftest.py under:
- https://docs.pytest.org/en/stable/fixture.html
- https://docs.pytest.org/en/stable/writing_plugins.html
"""
from pathlib import Path

import pytest as pytest
from pymatgen.core.structure import Structure


@pytest.fixture(scope='session')
def data_path():
    """Return the path to the data directory."""
    return Path(__file__).parent/"files"


@pytest.fixture(scope='session')
def make_single_struc(data_path):
    """Prepare required structure for testing"""
    filename = Path(data_path / 'silica.vasp')
    pmg_struc = Structure.from_file(filename)
    return pmg_struc
