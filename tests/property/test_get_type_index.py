import pytest
from glass.property.doas import get_type_index

def test_get_type_index():
    type_map = {"0": "H", "1": "O", "2": "N"}

    # Test with existing element
    assert get_type_index(type_map, "H") == 1
    assert get_type_index(type_map, "O") == 2
    assert get_type_index(type_map, "N") == 3

    # Test with non-existing element
    with pytest.raises(ValueError, match="Target element 'X' not found in type_map"):
        get_type_index(type_map, "X")