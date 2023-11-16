import copy
import glob
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Union

from pymatgen.core.structure import Structure
from pymatgen.io.vasp import Incar

from glass.utils import combine_files, get_bak_file


class PrepareVasp:
    def __init__(self,
                 save_path: Union[str, Path] = "./",
                 example_template: str = None,
                 incar_template: str = None,
                 kpt_template: str = None,
                 stru_template: str = None,
                 mix_incar: Dict[str, any] = {},
                 mix_kpt: List[Union[int, List[int]]] = [],
                 mix_stru: List[str] = [],
                 pp_dict: Dict[str, str] = {},
                 pp_path: str = None,
                 extra_files: List[str] = [],
                 bak_file = True,
                 no_link = False,) -> None:
        """To prepare inputs of vasp

        Args:
            save_path (Union[str, Path], optional):
                the pathe to store inputs. Defaults to "./".
            example_template (str, optional):
                folder name of an abacus inputs template, by default None.
                If specify input/kpt/stru_template, the related file in exmaple_template will
                be ingored. Defaults to None.
            input_template (str, optional):
                file name of INCAR template. Defaults to None.
            kpt_template (str, optional):
                file name of kpt template. Defaults to None.
            stru_template (str, optional):
                file name of STRU template. Defaults to None.
            mix_incar (Dict[str, any], optional):
                mixing setting of input parameters.
                Such as {"ENCUT": [200,300,400],
                         "KSPACING": [0.3,0.4,0.5]},
                then will prepare 3*3=9 inputs. Defaults to {}.
            mix_kpt (List[Union[int, List[int]]], optional):
                mixing setting of k point list. If the parameter
                is defined, then kpt_template will be invalid.
                Such as: [[1,1,1,0,0,0],
                          [2,2,2,0,0,0]],
                then will prepare 2 KPT files. Defaults to [].
            mix_stru (List[str])
            pp_dict (Dict[str, str], optional):
                a dictionary specify the pseudopotential files. Defaults to {}.
            pp_path (str, optional):
                the path of pseudopotential lib. Defaults to None.
            extra_files (List[str], optional):
                a list of some extra files that will be putted in each input. Defaults to [].
            bak_file (bool, optional):
                when save path exists, if bak_file is True, then back up the
                old files. Defaults to True.
            no_link (bool, optional):
                if True, then will not link the files in example template
                to save_path. Defaults to False.
        """
        self.save_path = save_path
        self.example_template = example_template
        self.incar_template = incar_template
        self.kpt_template = kpt_template
        self.stru_template = stru_template
        self.mix_incar = mix_incar
        self.pp_dict = pp_dict
        self.extra_files = extra_files
        self.mix_kpt = mix_kpt
        self.mix_stru = mix_stru

        self.pp_path = None if not pp_path else pp_path.strip()
        self.CollectPP()

        self.incar_list, self.incar_mix_param = self.Construct_incar_list()
        self.kpt_list = self.Construct_kpt_list()
        self.stru_list = self.Construct_stru_list()

        self.bak_file = bak_file
        self.no_link = no_link

        # when read the template file, will check if the template file folder is same as save_path
        # if same and final structures only one, then will not bak the template folder
        self.template_is_save_path = self.CheckIfTemplateIsSavePath()

    def CheckIfTemplateIsSavePath(self):
        if not os.path.exists(self.save_path):
            return False
        CheckedPath = []
        if self.incar_template:
            CheckedPath.append(Path(os.path.split(self.incar_template)[0]))
        if self.kpt_template:
            CheckedPath.append(Path(os.path.split(self.kpt_template)[0]))
        if self.stru_template:
            CheckedPath.append(Path(os.path.split(self.stru_template)[0]))
        if self.example_template:
            CheckedPath.append(Path(self.example_template))
        for ipath in CheckedPath:
            if Path(self.save_path).samefile(ipath):
                return True
        return False


    def CheckExtrafile(self, extrafiles: list) -> list:
        """Check whether the fila written extrafiles really exist

        Args:
            extrafiles (list): a list of file names

        Returns:
            _type_: Path of extrafiles
        """
        if not extrafiles:
            return []
        filelist = []
        for ifile in extrafiles:
            if os.path.isfile(ifile):
                filelist.append(ifile)
            else:
                print(f"ERROR: Cannot find {ifile}!")
        return filelist


    def CollectPP(self):
        """Assign the paths of provided pseudos to `self.pp_dict` attribute
           as a dictionary
        """
        if not self.pp_path:
            return
        if os.path.isdir(self.pp_path):
            # if os.path.isfile(os.path.join(self.pp_path, "element.json")):
            #     try:
            #         for k, v in json.load(open(os.path.join(self.pp_path, "element.json"))).item():
            #             if k not in self.pp_dict:
            #                 if os.path.isfile(os.path.join(self.pp_path, v)):
            #                     self.pp_dict[k] = os.path.join(self.pp_path, v)
            #     except:
            #         traceback.print_exc()
            # else:
            allfiles = os.listdir(self.pp_path)
            for ifile in allfiles:
                if not os.path.isfile(os.path.join(self.pp_path, ifile)): continue
                element_name = self.GetElementNameFromPot(ifile)
                if element_name and element_name not in self.pp_dict:
                    self.pp_dict[element_name] = os.path(self.pp_path, ifile)
        else:
            print(f"Not find pp dir: \'{self.pp_path}\'\n\tcurrent path: {os.getcwd()}")


    def GetElementNameFromPot(self, filename) -> str:
        with open(filename, 'r', encoding='utf-8') as f:
            first_line = f.readlines()[0]
            ele = first_line.split()[1]
        return ele


    def Construct_incar_list(self):
        """Prepare all possible incars

        Returns:
            _type_: _description_
        """
        all_incars = []
        incarf = None
        if self.example_template != None:
            if os.path.isfile(os.path.join(self.example_template, "INCAR")):
                incarf = os.path.join(self.example_template, "INCAR")
        if self.incar_template != None:
            if os.path.isfile(self.incar_template):
                incarf = self.incar_template
            else:
                print("WARNING: File %s is not found" % self.incar_template)

        print("INCAR: %s" % str(incarf))
        # incar_constant = {}
        if incarf != None:
            # incar_constant = PrepareVasp.ReadIncar(incarf)
            incar_constant = Incar.from_file(incarf)


        list_param = {}
        incar_constant_common = {}
        for k,v in self.mix_incar.items():
            #if value is list type, then we need prepare INPUT for each value
            #input_constant stores the parameters whose value is constant
            #list_param stores the parameters that has several values.
            if isinstance(v,(int,float,str)):
                incar_constant[k] = v
                incar_constant_common[k] = v
            elif isinstance(v,list):
                if len(v) == 1:
                    incar_constant[k] = v[0]
                    incar_constant_common[k] = v[0]
                else:
                    list_param[k] = v
                    if k in incar_constant:
                        del incar_constant[k]
            else:
                print("WARNING: type of '%s' is" % str(v),type(v),"will not add to INCAR")
                incar_constant[k] = v
        print("Invariant INCAR setting:",str(incar_constant))

        all_incars.append(incar_constant)
        for k,v in list_param.items():
            for i,iv in enumerate(v):
                if i == 0:
                    #if v only one value, add in all_inputs directly
                    for iinput in all_incars:
                        iinput[k] = iv
                else:
                    #if v has more than two values, deepcopy all_inputs and modify v, and then add to all_inputs
                    if i == 1:
                        tmp_incars = copy.deepcopy(all_incars)
                    for iinput in tmp_incars:
                        iinput[k] = iv
                    all_incars += copy.deepcopy(tmp_incars)

        return all_incars,[i for i in list_param.keys()]

    def Construct_kpt_list(self):
        """
        all_kpt is a list of list (6 element) or filename of KPT.
        If not specify mix_kpt and has specify the KPT template, will retrun a list
        of KPT filename, or will return a null list if no KPT template.
        """
        all_kpt = []

        kptf = None
        if self.example_template != None:
            if os.path.isfile(os.path.join(self.example_template,"KPOINTS")):
                kptf = os.path.join(self.example_template,"KPOINTS")
        if self.kpt_template != None:
            if os.path.isfile(self.kpt_template):
                kptf = self.kpt_template
            else:
                print("WARNING: File %s is not found" % self.kpt_template)

        if len(self.mix_kpt) == 0:
            if kptf != None:
                all_kpt.append(kptf)
            template_file = kptf
        else:
            for ikpt in self.mix_kpt:
                if isinstance(ikpt,int):
                    all_kpt.append([ikpt,ikpt,ikpt,0,0,0])
                elif isinstance(ikpt,list):
                    if len(ikpt) == 3:
                        all_kpt.append(ikpt+[0,0,0])
                    elif len(ikpt) == 6:
                        all_kpt.append(ikpt)
                    else:
                        print("mix_kpt should be a int or list of 3/6 elements, but not ",ikpt)
                elif isinstance(ikpt,str):
                    allkpt = glob.glob(ikpt)
                    allkpt.sort()
                    for iikpt in allkpt:
                        all_kpt.append(iikpt)
                else:
                    print("mix_kpt should be int or list of 3/6 elements, but not ",ikpt)
            template_file = self.mix_kpt
        print(f"KPT: {template_file}")
        return all_kpt

    def Construct_stru_list(self):
        all_stru = []
        struf = None
        if self.example_template != None:
            if os.path.isfile(os.path.join(self.example_template,"POSCAR")):
                struf = os.path.join(self.example_template,"POSCAR")
        if self.stru_template != None:
            if os.path.isfile(self.stru_template):
                struf = self.stru_template
            else:
                print("WARNING: File %s is not found" % self.stru_template)

        if len(self.mix_stru) == 0:
            if struf != None:
                all_stru.append(struf)
            else:
                print("Please set the stru_template!")
            template_file = struf
        else:
            for stru in self.mix_stru:
                allstrus = glob.glob(stru)
                allstrus.sort()
                for istru in allstrus:
                    all_stru.append(os.path.abspath(istru))
                if len(allstrus) == 0:
                    print("Structure file '%s' is not exist" % stru)
            template_file = self.mix_stru

        print(f"STRU: {template_file}")
        return all_stru

    def prepare(self):
        """
        """
        if not self.stru_list:
            print("No stru files, skip!!!")
            return None

        if not self.kpt_list:
            print("WARNING: not set KPOINTS")
            kpt_list = [None]
        else:
            kpt_list = self.kpt_list

        if not self.incar_list:
            incar_list = [None]
        else:
            incar_list = self.incar_list


        ipath = -1
        param_setting = {}
        cwd = os.getcwd()
        stru_num = len(self.stru_list) * len(kpt_list) * len(incar_list)
        for istru in self.stru_list:
            stru_data = Structure.from_file(istru)
            # stru_data = AbacusStru.ReadStru(istru)
            stru_path = os.path.split(istru)[0]
            if stru_path == "": stru_path = os.getcwd()
            # labels = stru_data.get_label()
            # labels = list(set(labels))
            labels = list(stru_data.symbol_set)
            linkstru = True
            allfiles = self.extra_files
            pp_list = []
            for ilabel in labels:
                #check pp file
                if ilabel not in self.pp_dict:
                    print(f"label {ilabel}: the pseudopotential of {ilabel} defined in {istru} is not found, skip this structure")
                    break
                else:
                    pp_list.append(os.path.split(self.pp_dict[ilabel])[1])  #only store the file name to pp_list
                    allfiles.append(combine_files(pp_list))
                    # allfiles.append(self.pp_dict[ilabel]) #store the whole pp file to allfiles
                # if not stru_data.get_pp() or pp_list[-1] != stru_data.get_pp()[i]:
                    # linkstru = False

            # stru_data.set_pp(pp_list)

            for ikpt in kpt_list:  #iteration of KPT
                for iinput in incar_list: #iteration of INPUT
                    ipath += 1
                    #create folder
                    #if not has_create_savepath:
                    #    if os.path.isdir(self.save_path):
                    #        bk = comm.GetBakFile(self.save_path)
                    #        shutil.move(self.save_path,bk)
                    #    has_create_savepath = True

                    # if only one stru, then do not create subfolder
                    if stru_num > 1:
                        save_path = os.path.join(self.save_path,str(ipath).zfill(5))
                    else:
                        save_path = self.save_path

                    if os.path.isdir(save_path) and \
                        (not Path(save_path).samefile(cwd)) and \
                        (self.bak_file) and \
                        (not self.template_is_save_path):
                            bk = get_bak_file(save_path)
                            shutil.move(save_path,bk)

                    if not os.path.isdir(save_path):
                        os.makedirs(save_path)

                    #store the param setting and path
                    param_setting[save_path] = [os.path.relpath(istru, cwd),ikpt,{}]
                    for input_param in self.incar_mix_param:
                        param_setting[save_path][-1][input_param] = iinput.get(input_param)

                    #create INPUT
                    if iinput != None:
                        iinput.write_file(os.path.join(save_path,"INCAR"))
                        # PrepareAbacus.WriteInput(iinput,os.path.join(save_path,"INPUT"))

                    #create KPT
                    if ikpt != None:
                        kptf = os.path.join(save_path,"KPT")
                        if isinstance(ikpt,str):
                            if os.path.isfile(kptf) and (not Path(ikpt).samefile(Path(kptf))):
                                os.unlink(kptf)

                            if not os.path.isfile(kptf):
                                if self.no_link:
                                    shutil.copy(os.path.abspath(ikpt),kptf)
                                else:
                                    os.symlink(os.path.abspath(ikpt),kptf)
                        elif isinstance(ikpt,list):
                            PrepareVasp.WriteKpt(ikpt,kptf)

                    #create STRU
                    struf = os.path.join(os.path.join(save_path,"POSCAR"))
                    if linkstru:
                        if os.path.isfile(struf) and (not Path(istru).samefile(Path(struf))):
                            os.unlink(struf)

                        if not os.path.isfile(struf):
                            if self.no_link:
                                shutil.copy(os.path.abspath(istru),struf)
                            else:
                                os.symlink(os.path.abspath(istru),struf)
                    else:
                        stru_data.to_file("POSCAR", "poscar")

                    #link other files
                    for ifile in allfiles:
                        ifile = os.path.abspath(ifile)
                        filename = os.path.split(ifile)[1]
                        target_file = os.path.join(save_path,filename)
                        if os.path.isfile(target_file) and not Path(ifile).samefile(Path(target_file)):
                            os.unlink(target_file)
                        if not os.path.isfile(target_file):
                            if self.no_link:
                                shutil.copy(ifile,target_file)
                            else:
                                os.symlink(ifile,target_file)
        return param_setting

    @staticmethod
    def WriteKpt(kpoint_list:List = [1,1,1,0,0,0],file_name:str = "KPT"):
        with open(file_name,'w') as f1:
            f1.write("K_POINTS\n0\nGamma\n")
            f1.write(" ".join([str(i) for i in kpoint_list]))


def CheckExample(example_path,description:str=""):
    print(f"Check ABACUS inputs: {example_path} {description}")
    if not os.path.isdir(example_path):
        print("Can not find example path %s" % example_path)
        return False
    if not os.path.isfile(os.path.join(example_path,"INPUT")):
        print("Can not find INPUT file in %s" % example_path)
        return False
    if not os.path.isfile(os.path.join(example_path,"STRU")):
        print("Can not find STRU file in %s" % example_path)
        return False
    iinput = Incar.from_file(os.path.join(example_path,"INPUT"))
    istru = Structure.from_file(os.path.join(example_path,"STRU"))

    if not istru:
        print("Read POSCAR file failed in %s" % example_path)
        return False

    cwd = os.getcwd()
    allpass = True
    os.chdir(example_path)
    # #check pp
    # ppfiles = istru.get_pp()
    # if not ppfiles:
    #     print("Can not find PP in %s" % example_path)
    #     allpass = False
    # else:
    #     for ppfile in ppfiles:
    #         real_ppfile = os.path.join(pp_path,ppfile)
    #         if not os.path.isfile(real_ppfile):
    #             print("Can not find PP file %s in %s" % (real_ppfile,example_path))
    #             allpass = False

    # check KPT
    # only basis is lcao and use gamma_only, or has define kspacing, KPT file is not needed
    gamma_only = iinput.get("gamma_only",False)
    kspacing = iinput.get("kspacing",None)
    if not (gamma_only or kspacing):
        if not os.path.isfile("KPT"):
            print("Can not find KPT file in %s" % example_path)
            allpass = False
    os.chdir(cwd)
    return allpass

def CommPath(pathlist):
    "return (commpath pathlist_without_commpath)"
    if len(pathlist) == 0:
        return None,pathlist
    commpath = os.path.commonpath(pathlist)
    if commpath != "":
        length = len(commpath) + 1
    else:
        length = 0
    return commpath,[i[length:] for i in pathlist]

def DoPrepare(
        param_setting: Dict[str, any],
        save_folder: str,
        no_link: bool = False
    ) -> List[Dict[str, dict]]:
    """
    param_setting is a dictionary like:
    {
        "example_template":["example_path"]
        "input_template":"INPUT",
        "kpt_template":"KPT",
        "stru_template":"STRU",
        "mix_input":{
            "ecutwfc":[50,60,70],
            "kspacing":[0.1,0.12,0.13]
        },
        "mix_kpt":[],
        "mix_stru":[],
        "pp_dict":{},
        "orb_dict":{},
        "pp_path": str,
        "orb_path": str,
        "dpks_descriptor":"",
        "extra_files":[],
        "mix_input_comment":"Do mixing for several input parameters. The diffrent values of one parameter should put in a list.",
        "mix_kpt_comment":"If need the mixing of several kpt setting. The element should be an int (eg 2 means [2,2,2,0,0,0]), or a list of 3 or 6 elements (eg [2,2,2] or [2,2,2,0,0,0]).",
        "mix_stru_commnet":"If need the mixing of several stru files. Like: ["a/stru","b/stru"],
    },

    save_folder specifies the destination of the new created examples.

    Return a list of dict, which is related to each example_template element. The key of the dict is the newcreated example path, and the value
    is the STRU/KPT/INPUT settings.
    """
    example_template = param_setting.get("example_template",None)
    if isinstance(example_template,str):
        example_template = glob.glob(example_template)
        example_template.sort()
    elif isinstance(example_template,list):
        tmp = copy.deepcopy(example_template)
        example_template = []
        for i in tmp:
            alli = glob.glob(i)
            alli.sort()
            example_template += alli
    else:
        example_template = [example_template]

    all_path_setting = []
    commpath,example_template_nocomm = CommPath(example_template)
    print(commpath,example_template_nocomm)
    for idx,iexample in enumerate(example_template):
        if len(example_template) > 1:
            save_path = os.path.join(save_folder,example_template_nocomm[idx])
            print("\n%s" % iexample)
        else:
            if Path(save_folder) == Path("."):
                save_path = commpath
            else:
                save_path = save_folder
        preparevasp = PrepareVasp(
            save_path=save_path,
            example_template=iexample,
            incar_template=param_setting.get("input_template", None),
            kpt_template=param_setting.get("kpt_template", None),
            stru_template=param_setting.get("stru_template", None),
            mix_incar=param_setting.get("mix_input", {}),
            mix_kpt=param_setting.get("mix_kpt", []),
            mix_stru=param_setting.get('mix_stru', []),
            pp_dict=param_setting.get("pp_dict", {}),
            pp_path=param_setting.get("pp_path", None),
            extra_files=param_setting.get("extra_files", []),
            bak_file=param_setting.get("bak_file", True),
            no_link=no_link
        )
        all_path_setting.append(preparevasp.prepare())

    return all_path_setting

def PrepareInput(param):
    param_setting_file = param.param
    save_folder = param.save
    if not os.path.isfile(param_setting_file):
        print("Can not find file %s!!!" % param_setting_file)
        sys.exit(1)

    param_setting = json.load(open(param_setting_file))
    if "prepare" in param_setting:
        param_setting = param_setting["prepare"]

    all_path_setting = DoPrepare(param_setting,save_folder,param.nolink)
    for path_setting in all_path_setting:
        if path_setting:
            for k,v in path_setting.items():
                print("%s:%s" % (k,str(v)))
