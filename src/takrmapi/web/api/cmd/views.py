"""CMD API views."""
from fastapi import APIRouter
from takrmapi.web.api.cmd.schema import LdapConnString


router = APIRouter()


@router.get("/run-something")
async def run_something() -> LdapConnString:
    """
    TODO do some dummy stuff...
    """

    return LdapConnString(
        success=True,
        ldap_conn_string="asd987sad98a7d9",
        ldap_user="d0f98gd0f9g8df09g8dg,",
        reason="vcb098cbv09c8bv0c8",
    )


@router.get("/run-something-cmd")
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
