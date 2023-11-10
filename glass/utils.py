import copy
import json
import os
from typing import Any, Optional, Type

import dflow
from dflow.plugins import bohrium
from dflow.plugins.bohrium import TiefblueClient
from dflow.plugins.dispatcher import DispatcherExecutor
from dflow.python import upload_packages

import glass

glass_path = os.path.split(glass.__file__)[0]


class InfoFlowTemplate(dict):
    """base template of input/output datas during the whole workflow

    Args:
        dict (_type_): default settings of parameters, defined in
        instance method get_default_dict
    """
    def __init__(
        self,
        ip_dict: Optional[dict] = None,
        init_class: Optional[Type[Any]] = None
    ):
        """class init

        Args:
            ip_dict (Optional[dict], optional):
                the dict to be written to the instance. Defaults to None.
            init_class (Optional[Type[Any]], optional):
                the inheritance class, which has newly defined get_default_dict
                instance method. Defaults to None.
        """
        if init_class:
            self.default_dict = init_class.get_default_dict()
        else:
            self.default_dict = InfoFlowTemplate.get_dedault_dict()
        dict_to_update = copy.deepcopy(self.default_dict)
        if not init_class:
            ip_dict = self.default_dict
        InfoFlowTemplate.update(dict_to_update, ip_dict)
        super().__init__(dict_to_update)

    @classmethod
    def get_default_dict(cls) -> dict:
        """set the default dict

        Returns:
            dict: defcult dict
        """
        default_dict = {"InfoFlowTemplate": "InfoFlowTemplate"}
        return default_dict

    @classmethod
    def update_dict(cls, d1: dict, d2: dict) -> dict:
        """update dict content

        Args:
            d1 (dict): the template dict, which is the dict to be updated
            d2 (dict): the wanted dict, which might not complete in keys

        Returns:
            dict: updated dict, with the wanted keys and values in.
            Specially, the original d1 dict will also be revised, which
            is the same as the returned one
        """
        for k, v in d2.items():
            if isinstance(v, dict) and k in d1 and isinstance(d1[k], dict):
                InfoFlowTemplate.update_dict(d1[k], v)
            else:
                d1[k] = v
        return d1

    def dump_to_json(
        self,
        out_filename: str = "param.json",
        *args,
        **kwargs
    ):
        """output json file

        Args:
            out_filename (str, optional): the output json filename. Defaults to "param.json".
        """
        with open(out_filename, 'w', encoding='utf-8') as f:
            json.dump(self, f, *args, **kwargs)

    def dump_to_file(self, out_filename: str = "param.dict"):
        """output InfoFlow to file.

        Args:
            out_filename (str, optional):
                output raw dict. Defaults to "param.dict".
        """
        with open(out_filename, "w", encoding="utf-8") as f:
            f.write(str(self))

    def load_from_json(
            self,
            load_filename: str,
            *args,
            **kwargs):
        """update InfoFlow from json file

        Args:
            load_filename (str): the json file to be load
        """
        with open(load_filename, "r", encoding='utf-8') as f:
            read_param = json.load(f, *args, **kwargs)
        InfoFlowTemplate.update_dict(self, read_param)

    def load_from_dict(
            self,
            load_filename: str,
            ):
        """update InfoFlow from .dict file

        Args:
            load_filename (str): the raw dict file to be load
        """
        with open(load_filename, "r", encoding="utf-8") as f:
            txt = f.read()
        read_param = eval(txt)
        InfoFlowTemplate.update_dict(self, read_param)



class Mdata(InfoFlowTemplate):
    def __init__(
        self,
        ip_dict: Optional[dict] = None
    ):
        self.default_dict = Mdata.get_default_dict()
        super().__init__(ip_dict, Mdata)
        self.check()
        self.post_treat()

    @classmethod
    def get_default_dict(cls) -> dict:
        """set default dict

        Returns:
            dict: default dict
        """
        default_dict = {
            "dflow_config":{
                "host": "https://workflows.deepmodeling.com",
                "k8s_api_server": "https://workflows.deepmodeling.com"
            },
            "bohrium_config":{
                "username": "<YOUR-BOHRIUM-USERNAME>",
                "password": "<YOUR-BOHRIUM-PASSWORD>",
                "ticket": "<YOUR-BOHRIUM-TICKET>",
                "project_id": "<project id in str>",
            },
            "dispatcher": {
                "batch_type": "Bohrium",
                "context_type": "Bohrium",
                "input_data": {
                    "job_type": "container",
                    "platform": "ali",
                    "scass_type": "c2_m4_cpu",
                    "log_file": "*.output"
                }
            },
        }
        return default_dict

    def post_treat(self) -> None:
        """treat P2DMdata after init
        """
        self.post_password_and_ticket()

    def check(self) -> None:
        """treat P2DMdata after init
        """

    def post_password_and_ticket(self):
        """if no password or ticket input, delete the key.
        """
        default_password = Mdata.get_default_dict()["bohrium_config"]["password"]
        default_ticket = Mdata.get_default_dict()["bohrium_config"]["ticket"]
        # if no one exists
        if self["bohrium_config"]["password"] == default_password:
            self["bohrium_config"].pop("password")
        if self["bohrium_config"]["ticket"] == default_ticket:
            self["bohrium_config"].pop("ticket")
        # when both not exits, not raise error for the support of other
        # dpdispatcher settings without bohrium.

def config_argo(**config):
    upload_packages.append(glass_path)
    #print(config)

    if dflow.config["mode"] == "debug": return

    if config["dflow_config"]:
        for k, v in config["dflow_config"].items():
            dflow.config[k] = v

    if config["bohrium_config"]:
        #print(bohrium)
        if "username" in config["bohrium_config"]:
            bohrium.config["username"] = config["bohrium_config"].pop("username")
        # 将外层获取的 ticket 设置到 dflow.plugins.bohrium.config 中

        if "ticket" in config["bohrium_config"] :
            print("config bohrium config ticket set"
            #, config["bohrium_config"]
            )
            bohrium.config["ticket"] = config["bohrium_config"].pop("ticket")
        if "password" in config["bohrium_config"] :
            print("config bohrium config password set")
            bohrium.config["password"] = config["bohrium_config"].pop("password")

        if ("ticket" in config["bohrium_config"]
           and "password" in config["bohrium_config"]):
            print("Warning: both bohrium ticket and password exists")

        for k, v in config["bohrium_config"].items():
            print("config bohrium config k", k, "v", v)
            bohrium.config[k] = v

    # s3_config
    dflow.s3_config["repo_key"] = "oss-bohrium"
    dflow.s3_config["storage_client"] = TiefblueClient()

def dispatcher_executor(**config_para):
    return DispatcherExecutor(
        machine_dict={
            "batch_type": config_para["dispatcher"].get("batch_type"),
            "context_type": config_para["dispatcher"].get("context_type"),
            "remote_profile": {"input_data": config_para["dispatcher"].get("input_data")}
            },
            image_pull_policy = "IfNotPresent")
