import filecmp
from pathlib import Path

import pytest

from glass.io.input import convert_to_lmp_data


def test_convert_to_lmp_data(tmp_path, make_single_struc, data_path):
    pmg_struc = make_single_struc
    convert_to_lmp_data(pmg_struc, {"1": "Si", "2": "O"}, {"Si": 28.085, "O":15.999})
    compare = filecmp.cmp(tmp_path / 'lmp.data', data_path / 'ref_lmp.data')
    assert compare