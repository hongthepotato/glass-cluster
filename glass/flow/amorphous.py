import json
from pathlib import Path
from typing import Union

from dflow import Step, Workflow, argo_range, upload_artifact
from dflow.plugins.dispatcher import DispatcherExecutor
from dflow.python import PythonOPTemplate, Slices

from glass.io.input_op import MDInputPrepOP, StrucPrepOP
from glass.property.doas_op import GraspSnapShotOP, PlotDoas
from glass.simulation.dp_run_op import DpRunOP
from glass.utils import Mdata, config_argo, dispatcher_executor


def amorphous_flow(
    executor_run: DispatcherExecutor = None,
    dflow_labels = None,
    **pdata
) -> Workflow:

    wf = Workflow(
        name='amorphous',
        labels=dflow_labels,
    )

    if struc_file := pdata.get("structure"):
        struc = upload_artifact(struc_file)

    if in_lmp_file := pdata.get("in_lmp"):
        in_lmp = upload_artifact(in_lmp_file)
    else:
        in_lmp = None

    if model_file := pdata.get("model"):
        model = upload_artifact(model_file)

    prep_struc = Step(
        name="prep_struc",
        template=PythonOPTemplate(
            StrucPrepOP,
            image="pymatgen contained"
        ),
        artifacts={
            "struc_file": struc
        },
        key="prep-struc"
    )

    wf.add(prep_struc)

    prep_MD_input = Step(
        name="prep_md_input",
        template=PythonOPTemplate(
            MDInputPrepOP,
            image="pymatgen contained"
        ),
        parameters={
            "processes": pdata["processes"],
            "pmg_struc": prep_struc.outputs.parameters["pmg_struc"],
            "type_map": pdata["type_map"],
            "mass_map": pdata["mass_map"]
        },
        artifacts={
            "in_lmp": in_lmp,
            "model": model,
        },
        key="prep-md-input"
    )

    wf.add(prep_MD_input)

    run_md = Step(
        name="run_md",
        template=PythonOPTemplate(
            DpRunOP,
            image="deepmd"
        ),
        artifacts={
            "work_dir": prep_MD_input.outputs.artifacts["run_path"]
        },
        executor=executor_run,
        key='run-dp'
    )

    wf.add(run_md)

    doas_idx = pdata["properties"]["doas"]["_idx"]
    for mini_dict in pdata["processes"]:
        if mini_dict["_idx"] == doas_idx:
            traj_name = mini_dict["params"]["traj_file_name"]

    grasp_snap = Step(
        name="grasp_snapshot",
        template=PythonOPTemplate(
            GraspSnapShotOP,
            image="any"
        ),
        artifacts={
            "md_run": run_md.outputs.artifacts["dp_dir"],
            "model": model
        },
        parameters={
            "traj_file_name": traj_name,
            "energy_n_frame": pdata["properties"]["doas"]["every_n_frame"],
            "type_map": pdata["type_map"],
            "mass_map": pdata["mass_map"]
        },
        key='grasp-snap'
    )

    wf.add(grasp_snap)

    minimize_snap = Step(
        name="mini_snapshot",
        template=PythonOPTemplate(
            DpRunOP,
            image="deepmd",
            slices=Slices(
                "{{item}}",
                input_artifact=["work_dir"],
                output_artifact=["dp_dir"]
            )
        ),
        artifacts={
            "work_dir": grasp_snap.outputs.artifacts["minimize_dirs"]
        },
        with_param=argo_range(grasp_snap.outputs.parameters["num_minimize"]),
        key="mini-snap-{{item}}",
        executor=executor_run
    )

    wf.add(minimize_snap)

    plot_doas = Step(
        name="plot_doas",
        template=PythonOPTemplate(
            PlotDoas,
            image="any",
            artifacts={
                "minimize_dirs": minimize_snap.outputs.artifacts["dp_dir"]
            },
            parameters={
                "target_element": pdata["properties"]["doas"]["target_element"],
                "bins": pdata["properties"]["doas"]["bins"],
                "type_map": pdata["type_map"]
            }
        )
    )

    wf.add(plot_doas)

    return wf

def main_amorphous_flow(
    pdata_file: Union[str, Path] = "param.json",
    mdata_file: Union[str, Path] = "machine.json",
    dflow_labels = None
):
    with open(pdata_file, 'r', encoding='utf-8') as f:
        pdata = json.load(f)
    with open(mdata_file, 'r', encoding='utf-8') as f:
        mdata_dict = json.load(f)
    mdata = Mdata(mdata_dict)
    config_argo(**mdata)
    executor_run = dispatcher_executor(**mdata)
    wf = amorphous_flow(
        executor_run=executor_run,
        dflow_labels=dflow_labels,
        **pdata
    )
