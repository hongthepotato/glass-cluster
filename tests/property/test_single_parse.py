from glass.property.doas import parse_single


def test_parse_single(data_path):
    out_data = parse_single(
        data_path / "dump.atom_energy",
        "Bi",
        {"0": "Si", "1": "O", "2":"Bi"}
    )
    ref_data = [['216', '3', '-1849.08']]
    assert out_data == ref_data
