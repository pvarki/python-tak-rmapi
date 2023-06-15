"""CMD API views."""
from fastapi import APIRouter, Request, Body
from takrmapi.web.api.cmd.schema import DoSomeThingIn, DoSomeThingOut, LdapConnString
from ....commands import commandtools, CmdParamsIn

router = APIRouter()


@router.post("/run-something", response_model=DoSomeThingOut)
async def run_something(
    request: Request,
    request_in: DoSomeThingIn = Body(
        None,
        examples=DoSomeThingIn.Config.schema_extra["examples"],
    ),
) -> DoSomeThingOut:
    """
    TODO do some dummy stuff...
    """

    # Content-Type: application/json
    _header_ctype = request.headers.get("Content-Type")
    if "application/json" != _header_ctype:
        return DoSomeThingOut(
            success=False, reason="'Content-Type: application/json' header missing", rcode=665, stdout="na", stderr=""
        )
    _p: CmdParamsIn = {
        "command": request_in.cmd_str,
        "cmd_mode": request_in.cmd_mode,
        "allow_semicolon": request_in.cmd_allow_semicolon,
        "cmd_base64": request_in.cmd_base64,
        "docker_container_id": request_in.docker_container_id,
        "docker_interactive_exec": request_in.docker_interactive_exec,
        "az_resource_group": request_in.az_resource_group,
        "az_container_group_name": request_in.az_container_group_name,
        "az_container_name": request_in.az_container_group_name,
    }

    _res = await commandtools.run_cmd(_p)

    # print(_res)

    # -v “/var/run/docker.sock:/var/run/docker.sock”
    # Note - Please provide read,write access to the user for /var/run/docker.sock file on Linux.

    #    version: '2.1'
    #
    #    services:
    #
    #    site:
    #        image: ubuntu
    #        container_name: test-site
    #        command: sleep 999999
    #
    #    dkr:
    #        image: docker
    #        privileged: true
    #        working_dir: "/dkr"
    #        volumes:
    #        - ".:/dkr"
    #        - "/var/run/docker.sock:/var/run/docker.sock"
    #        command: docker ps -a

    # {request_in.cmd_mode}
    return DoSomeThingOut(
        success=_res["success"],
        reason=_res["reason"],
        rcode=_res["rcode"],
        stdout=_res["stdout"],
        stderr=_res["stderr"],
    )


@router.get("/run-something-docker")
async def run_something_cmd() -> LdapConnString:
    """
    TODO do some dummy stuff in subprocess/cmd or somethings..
    """

    return LdapConnString(
        success=True,
        ldap_conn_string="qwuyquwieqwiueyqiue",
        ldap_user="9q8we7a98ds7sa9d87,",
        reason="dsa987dsa98a7ds987",
    )
