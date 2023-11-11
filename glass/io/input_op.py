import shutil
from pathlib import Path
from typing import List

from dflow.python import OP, OPIO, Artifact, OPIOSign, Parameter
from pymatgen.core.structure import Structure

from glass.io.input import build_in_lmp, convert_to_lmp_data, get_dope


class DopeStrucPrep(OP):
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
            "compen_type": Parameter(str),
            "type_map": Parameter(dict),
            "mass_map": Parameter(dict)
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
        type_map = op_in["type_map"]
        mass_map = op_in["mass_map"]
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


class MDInputPrepOP(OP):
    r"""
    This is a OP used to prep Input
    """

    @classmethod
    def get_input_sign(cls) -> OPIOSign:
        return OPIOSign({
            # "dir_path": Artifact(Path),
            "processes": Parameter(List[dict], default=None),
            "in_lmp": Artifact(Path),
            "model": Artifact(Path),
            "pmg_struc": Artifact(Path),
            "type_map": Parameter(dict),
            "mass_map": Parameter(dict)
        })

    @classmethod
    def get_output_sign(cls) -> OPIOSign:
        return OPIOSign({
            "run_path": Artifact(Path)
        })

    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        # dir_path = op_in["dir_path"]
        dir_path = Path("MD_input")
        dir_path.mkdir(exist_ok=True)
        model = op_in["model"]
        struc = op_in["pmg_struc"]
        pmg_struc = Structure.from_file(struc)
        type_map = op_in["type_map"]
        mass_map = op_in["mass_map"]
        file_path = convert_to_lmp_data(pmg_struc, type_map, mass_map, dir_path)
        in_lmp = op_in["in_lmp"]
        if in_lmp:
            shutil.move(in_lmp, dir_path)
        else:
            processes = op_in["processes"]
            build_in_lmp(processes, model.name, file_path.name, dir_path)
        op_out = {
            "run_path": dir_path
        }
        return op_out
