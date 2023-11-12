from glass.io.input import convert_to_lmp_data


def compare_files(file1, file2):
    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

        # 去除行尾的空格和换行符
        stripped_lines1 = [line.rstrip() for line in lines1]
        stripped_lines2 = [line.rstrip() for line in lines2]

        return stripped_lines1 == stripped_lines2

def test_convert_to_lmp_data(tmp_path, make_single_struc, data_path):
    file_path = convert_to_lmp_data(
        make_single_struc,
        {"0": "Si", "1": "O"},
        {"Si": 28.085, "O":15.999},
        tmp_path
    )
    result = compare_files(file_path, data_path / 'ref_lmp.data')
    assert result
