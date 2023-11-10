import argparse


def main():
    parser = argparse.ArgumentParser(
        prog='glass',
        description="""WTF"""
    )
    subparsers = parser.add_subparsers()

    # parser_dft_param_test
    parser_dft_param = subparsers.add_parser(
        "dft_param_test",
        help="WTF"
    )
    parser_dft_param.add_argument(
        "-m",
        "--machine",
        type=str,
        help="SORRY"
    )
    parser_dft_param.add_argument(
        "-p",
        "--parameter",
        type=str,
        help=""
    )

    # parser_amorphous_test
    parser_amorphous_test = subparsers.add_parser(
        "amorphous_test",
        help=""
    )
    parser_amorphous_test.add_argument(
        "-m",
        "--machine",
        type=str,
        help=""
    )
    parser_amorphous_test.add_argument(
        "-p",
        "--parameter",
        type=str,
        help=""
    )
