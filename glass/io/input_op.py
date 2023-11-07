from pathlib import Path
import shutil
from pymatgen.core.structure import Structure
from dflow.python import (
    OP,
    OPIO,
    Artifact,
    OPIOSign,
    Parameter,
)
from glass.io.input import get_dope, convert_to_lmp_data

class StrucPrep(OP):
    r"""
    This is a OP used to prep Structure
    """

    @classmethod
    def get_input_sign(cls) -> OPIOSign:
        return OPIOSign({
            "filename": Parameter(str),
            "method": Parameter(str),
            "dopant_ratio": Parameter(float),
            "remove_type": Parameter(str),
            "dopant_type": Parameter(str),
            "compen_ratio": Parameter(float),
            "compen_type": Parameter(str)
        })

    @classmethod
    def get_output_sign(cls) -> OPIOSign:
        return OPIOSign({
            "dir_path": Artifact(Path)
        })

    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        filename = op_in["filename"]
        method = op_in["method"]
        dopant_ratio = op_in["dopant_ratio"]
        remove_type = op_in["remove_type"]
        dopant_type = op_in["dopant_type"]
        compen_ratio = op_in["compen_ratio"]
        compen_type = op_in["compen_type"]
        structure = Structure.from_file(filename)
        new_structure = get_dope(
            structure, method,
            dopant_ratio,
            remove_type,
            dopant_type,
            compen_ratio,
            compen_type
        )
        dir_path = convert_to_lmp_data(new_structure, type_map, mass_map)
        op_out = {
            "dir_path": dir_path
        }
        return op_out


class InputPrep(OP):
    r"""
    This is a OP used to prep Input
    """
    @classmethod
    def get_input_sign(cls) -> OPIOSign:
        return OPIOSign({
            "dir_path": Artifact(Path),
            "processes": dict,
            "provided_in_lmp": bool,
            "in_lmp": Artifact(Path)
        })

    @classmethod
    def get_output_sign(cls) -> OPIOSign:
        return OPIOSign({
            "run_path": Artifact(Path)
        })

    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        dir_path = op_in["dir_path"]
        provided_in_lmp = op_in["provided_in_lmp"]
        if provided_in_lmp:
            in_lmp = op_in["in_lmp"]
            shutil.move(in_lmp, dir_path)
        else:
            pass

        op_out = {
            "run_path": dir_path
        }

        return op_out
