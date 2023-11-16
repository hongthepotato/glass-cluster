import argparse

from glass.flow.amorphous import main_amorphous_flow


def amorphous_flow(args):
    main_amorphous_flow(
        pdata_file=args.parameter,
        mdata_file=args.machine,
        path=args.output
    )

def main():
    parser = argparse.ArgumentParser(
        prog='glass',
        description="""WTF"""
    )
    subparsers = parser.add_subparsers()

    # parser_dft_param_test
    parser_dft_param = subparsers.add_parser(
        "dft_param_test",
        help="For DFT parameters testing like kspacing, only VASP for now"
    )
    parser_dft_param.add_argument(
        "-m",
        "--machine",
        type=str,
        help="User-defined configuration file"
    )
    parser_dft_param.add_argument(
        "-p",
        "--parameter",
        type=str,
        help="parameter file for current task"
    )

    # parser_amorphous_test
    parser_amorphous_test = subparsers.add_parser(
        "amorphous_test",
        help="Amorphous test for DP and DFT"
    )
    parser_amorphous_test.add_argument(
        "-m",
        "--machine",
        type=str,
        help="User-defined configuration file"
    )
    parser_amorphous_test.add_argument(
        "-p",
        "--parameter",
        type=str,
        help="parameter file for current task"
    )
    parser_amorphous_test.add_argument(
        "-o",
        "--output",
        type=str,
        help="Path for download output files",
        default="./"
    )
    parser_amorphous_test.set_defaults(handler=amorphous_flow)

    # parser arguments actually
    args = parser.parse_args()
    if hasattr(args, 'handler'):
        # print(args)
        args.handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
