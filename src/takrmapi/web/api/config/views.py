"""Config API views."""
from fastapi import APIRouter
from takrmapi.web.api.config.schema import LdapConnString


router = APIRouter()


@router.get("/active-config")
async def active_config() -> LdapConnString:
    """
    TODO get / set some config to somewhere...
    """

    return LdapConnString(
        success=True,
        ldap_conn_string="ertyuiop",
        ldap_user="qoiwelkd,",
        reason="e567uikqwe",
    )
