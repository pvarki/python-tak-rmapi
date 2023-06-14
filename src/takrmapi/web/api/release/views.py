"""Release API views."""
from fastapi import APIRouter
from takrmapi.web.api.release.schema import LdapConnString

router = APIRouter()


@router.get("/download-text")
async def dl_text() -> LdapConnString:
    """
    TODO test for text download...
    """

    return LdapConnString(
        success=True,
        ldap_conn_string="dfghjklö",
        ldap_user="cvbnm,",
        reason="qweiukjdsa",
    )


@router.get("/download-package")
async def dl_package() -> LdapConnString:
    """
    TODO some sort of package download zip thingy...
    """

    return LdapConnString(
        success=True,
        ldap_conn_string="dsadsada",
        ldap_user="jupjuojuoojuojuoj",
        reason="qwewqeqweqwewqe",
    )
