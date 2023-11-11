import os
from pathlib import Path

from dflow.python import OP, OPIO, Artifact, OPIOSign


class DpRunOP(OP):
    """_summary_

    Args:
        OP (_type_): _description_
    """

    @classmethod
    def get_input_sign(cls) -> OPIOSign:
        return OPIO({
            "work_dir": Artifact(Path)
        })

    @classmethod
    def get_output_sign(cls) -> OPIOSign:
        return OPIOSign({
            "dp_dir": Artifact(Path)
        })

    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        work_dir = op_in["work_dir"]
        command = "lmp < in.lmp"
        os.chdir(work_dir)
        os.system(command)
        op_out = {
            "dp_dir": op_in["work_dir"]
        }
        return op_out
