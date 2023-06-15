"""" Module to run commands """
from typing import TypedDict, Optional
import base64
import binascii
import asyncio
import shlex


class CmdParamsIn(TypedDict):
    """run_cmd params typed dict"""

    command: str
    cmd_mode: str
    cmd_base64: bool
    allow_semicolon: bool
    docker_container_id: str
    docker_interactive_exec: bool
    az_resource_group: str
    az_container_group_name: str
    az_container_name: str

    # command: str = "",
    # cmd_mode: str = "",
    # cmd_base64: bool = False,
    # allow_semicolon: bool = False,
    # docker_container_id: str = "",
    # docker_interactive_exec: bool = False,
    # az_resource_group: str = "",
    # az_container_group_name: str = "",
    # az_container_name: str = "",


class CmdResponse(TypedDict):
    """response typed dict"""

    success: bool
    reason: str
    rcode: Optional[int]
    stdout: str
    stderr: str


class CommandTools:  # pylint: disable=too-few-public-methods
    """tools to run command either in local / remote / dockerized environments"""

    def __init__(self) -> None:
        self.returnable: CmdResponse = {
            "success": False,
            "reason": "Default init values. If you see this, it's definately bad response.",
            "rcode": 666,
            "stdout": "",
            "stderr": "",
        }
        self.command: str = ""

    def check_params(self, _p: CmdParamsIn) -> bool:
        """Check input params for run_cmd"""

        _return_bool: bool = True
        # Return -f Empty cmd_mode variable
        if _p["cmd_mode"] == "":
            _return_bool = False
            self.returnable = {
                "success": False,
                "reason": "Value for variable 'cmd_mode' is not defined.",
                "rcode": 666,
                "stdout": "",
                "stderr": "",
            }

        # Return if cmd_mode variable not in allowed list
        if _p["cmd_mode"] not in ["local", "docker", "azure-container-service"]:
            _return_bool = False
            self.returnable = {
                "success": False,
                "reason": "Value for variable 'cmd_mode' not in predeined list. Please check your variables...",
                "rcode": 666,
                "stdout": "",
                "stderr": "",
            }

        # Return if Empty command string
        if _p["command"] == "":
            _return_bool = False
            self.returnable = {
                "success": False,
                "reason": "Empty command string, please define command for 'command' variable",
                "rcode": 666,
                "stdout": "",
                "stderr": "",
            }
        # Return if empty id when docker is used
        if _p["cmd_mode"] == "docker" and _p["docker_container_id"] == "":
            _return_bool = False
            self.returnable = {
                "success": False,
                "reason": "docker_container_id cannot be empty if cmd_mode is set to 'docker'",
                "rcode": 666,
                "stdout": "",
                "stderr": "",
            }
        # Return if empty rg/group/name when azure-container-service is used
        if _p["cmd_mode"] == "azure-container-service" and (
            _p["az_resource_group"] == "" or _p["az_container_group_name"] == "" or _p["az_container_name"] == ""
        ):
            _return_bool = False
            self.returnable = {
                "success": False,
                "reason": "az_resource_group or az_container_group_name or az_container_name"
                + " cannot be empty if cmd_mode is set to 'azure-container-service'",
                "rcode": 666,
                "stdout": "",
                "stderr": "",
            }

        return _return_bool

    def extract_cmd_from_maybe_base64(self, _p: CmdParamsIn) -> bool:
        """Convert command from base64 if needed and return command as string"""
        _return_bool: bool = True
        if _p["cmd_base64"] is True:
            try:
                _cmd_decoded = base64.b64decode(_p["command"])
                _cmd_str = _cmd_decoded.decode("utf-8").strip()
                self.command = _cmd_str
            except binascii.Error as _e:
                _return_bool = False
                self.returnable = {
                    "success": False,
                    "reason": f"Unable to decode base64 encoded string - binascii.Error: {_e}",
                    "rcode": 666,
                    "stdout": "",
                    "stderr": "",
                }
        else:
            self.command = _p["command"]

        # Deny command if ; found and it's not allowed
        if _return_bool is not False and ";" in self.command and _p["allow_semicolon"] is False:
            _return_bool = False
            self.returnable = {
                "success": False,
                "reason": "allow_semicolon variable is False and semicolon was found in command",
                "rcode": 666,
                "stdout": "",
                "stderr": "",
            }

        return _return_bool

    def modify_command_if_needed(self, _p: CmdParamsIn) -> None:
        """Add extra parameters to self.command based on the command target"""

        # Accept local cmd as is --> No need to do anything...
        # if _p["cmd_mode"] == "local":
        #    _cmd = command

        if _p["cmd_mode"] == "docker":
            _tmp_cmd = shlex.quote(self.command)
            _cmd_interactive: str = " "
            if _p["docker_interactive_exec"] is True:
                _cmd_interactive = "-i "
            self.command = f"docker exec {_cmd_interactive} {_p['docker_container_id']} /bin/sh -c {_tmp_cmd}"

        elif _p["cmd_mode"] == "azure-container-service":
            _tmp_cmd = shlex.quote(self.command)
            self.command = f"az container exec --resource-group {_p['az_resource_group']} \
 --name {_p['az_container_group_name']} --container-name {_p['az_container_name']} --exec-command {_tmp_cmd}"

    async def execute_asyncio_cmd(self, _p: CmdParamsIn) -> bool:
        """Execute cmd as asyncio"""
        _return_bool: bool = True

        _rcode: Optional[int] = 666
        _stdout: bytes = b""
        _stderr: bytes = b""
        print(self.command)
        try:
            # Local command as is
            if _p["cmd_mode"] == "local":
                proc = await asyncio.create_subprocess_shell(
                    self.command, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
                )
                _stdout, _stderr = await proc.communicate()
                _rcode = proc.returncode
            # Docker command as is...
            # TODO insert some extra docker stuff here if needed
            elif _p["cmd_mode"] == "docker":
                proc = await asyncio.create_subprocess_shell(
                    self.command, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
                )
                _stdout, _stderr = await proc.communicate()
                _rcode = proc.returncode
            # azure-container-service command as is...
            # TODO insert some extra azure-container-service stuff here if needed
            elif _p["cmd_mode"] == "azure-container-service":
                _stdout = b"not implemented"
                _stderr = b"suck my rock"
                _rcode = 123
            # Not implemented....
            else:
                _return_bool = False
                self.returnable = {
                    "success": False,
                    "reason": f"cmd_mode '{_p['cmd_mode']}' not yet implemented",
                    "rcode": _rcode,
                    "stdout": "",
                    "stderr": "",
                }

        # Exception in running command
        except Exception as _e:  # pylint: disable=broad-except
            _return_bool = False
            self.returnable = {
                "success": False,
                "reason": f"Exception during running command. Exception : {_e}",
                "rcode": 999,
                "stdout": "",
                "stderr": "",
            }

        # Non zero return code
        if _return_bool is True and _rcode != 0:
            _return_bool = False
            self.returnable = {
                "success": False,
                "reason": "Non zero return code",
                "rcode": _rcode,
                "stdout": _stdout.decode("utf-8"),
                "stderr": _stderr.decode("utf-8"),
            }

        # OK result in the end...
        if _return_bool is True:
            self.returnable = {
                "success": True,
                "reason": "",
                "rcode": _rcode,
                "stdout": _stdout.decode("utf-8"),
                "stderr": _stderr.decode("utf-8"),
            }

        return _return_bool

    async def run_cmd(self, _p: CmdParamsIn) -> CmdResponse:
        """
        command[str] : Some command, on default multiple commands by splitting using ; is denied.\n
        cmd_mode[str] : Destination for command. For now accepted values are [local/docker/azure-container-service]\n
        cmd_base64[bool][False] : Command is base64 encoded.\n
        allow_semicolon[bool][False] : Allow multiple commands splitted by semicolon(;)\n
        docker_container_id[str] : ID/name for the container where command is issued.\n
        docker_interactive_exec[bool][False] : Set interactive flag for docker command.\n
        az_resource_group[str] : Resource group name in azure container service.\n
        az_container_group_name[str] : Container group name in azure container service.\n
        az_container_name[str] : Container name in azure container service.\n
        \n
        \n
        return CmdResponse {\n
            "success": True/False\n
            "reason": ""/"Non zero return code"/"Some other reason"\n
            "rcode": 666/actual return code from command\n
            "stdout": "stdout output from command"\n
            "stderr": "stderr output from command"\n
        }
        """

        # Initial check for params.
        _return_check: bool = self.check_params(_p)
        if _return_check is False:
            return self.returnable

        # Convert base64 to self.command if needed or use as is...
        _return_check = self.extract_cmd_from_maybe_base64(_p)
        if _return_check is False:
            return self.returnable

        # Set some extra stuff to command if it targets docker
        self.modify_command_if_needed(_p)

        # Run the actual command as asyncio
        _return_check = await self.execute_asyncio_cmd(_p)

        return self.returnable


commandtools = CommandTools()
