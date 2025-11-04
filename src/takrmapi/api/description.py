"""Descriptions API"""

from typing import Optional, Literal
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Extra, Field  # pylint: disable=(no-name-in-module # false-positive

LOGGER = logging.getLogger(__name__)

router = APIRouter()  # These endpoints are public
router_v2 = APIRouter()


# FIXME: Move to libpvarki
class ProductDescription(BaseModel):  # pylint: disable=too-few-public-methods
    """Description of a product"""

    shortname: str = Field(description="Short name for the product, used as slug/key in dicts and urls")
    title: str = Field(description="Fancy name for the product")
    icon: Optional[str] = Field(description="URL for icon")
    description: str = Field(description="Short-ish description of the product")
    language: str = Field(description="Language of this response")

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic configs"""

        extra = Extra.forbid


class ProductComponent(BaseModel):  # pylint: disable=too-few-public-methods
    """Project component info"""

    type: Literal["link", "markdown", "component"]
    ref: str


class ProductDescriptionExtended(BaseModel):  # pylint: disable=too-few-public-methods
    """Description of a product"""

    shortname: str = Field(description="Short name for the product, used as slug/key in dicts and urls")
    title: str = Field(description="Fancy name for the product")
    icon: Optional[str] = Field(description="URL for icon")
    description: str = Field(description="Short-ish description of the product")
    language: str = Field(description="Language of this response")
    docs: str = Field(description="Link to documentation")
    component: ProductComponent = Field(description="Component type and ref")

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic configs"""

        extra = Extra.forbid


@router.get(
    "/{language}",
    response_model=ProductDescription,
)
async def return_product_description(language: str) -> ProductDescription:
    """Fetch description from each product in manifest"""
    if language == "fi":
        # FIXME: Localize
        return ProductDescription(
            shortname="tak",
            title="TAK: Team Awareness Kit",
            icon=None,
            description="Situational awareness system",
            language="en",
        )
    if language == "sv":
        # FIXME: Localize
        return ProductDescription(
            shortname="tak",
            title="TAK: Team Awareness Kit",
            icon=None,
            description="Situational awareness system",
            language="en",
        )
    # Fall back to English
    return ProductDescription(
        shortname="tak",
        title="TAK: Team Awareness Kit",
        icon=None,
        description="Situational awareness system",
        language="en",
    )


@router_v2.get(
    "/{language}",
    response_model=ProductDescriptionExtended,
)
async def return_product_description_extended(language: str) -> ProductDescriptionExtended:
    """Fetch description from each product in manifest"""

    if language == "fi":
        # FIXME: Localize
        return ProductDescriptionExtended(
            shortname="tak",
            title="TAK: Team Awareness Kit",
            icon=None,
            description="Situational awareness system",
            language="en",
            docs="https://pvarki.github.io/Docusaurus-docs/docs/android/deployapp/home/",
            component=ProductComponent(type="component", ref="/ui/tak/remoteEntry.js"),
        )
    if language == "sv":
        # FIXME: Localize
        return ProductDescriptionExtended(
            shortname="tak",
            title="TAK: Team Awareness Kit",
            icon=None,
            description="Situational awareness system",
            language="en",
            docs="https://pvarki.github.io/Docusaurus-docs/docs/android/deployapp/home/",
            component=ProductComponent(type="component", ref="/ui/tak/remoteEntry.js"),
        )
    # Fall back to English
    return ProductDescriptionExtended(
        shortname="tak",
        title="TAK: Team Awareness Kit",
        icon=None,
        description="Situational awareness system",
        language="en",
        docs="https://pvarki.github.io/Docusaurus-docs/docs/android/deployapp/home/",
        component=ProductComponent(type="component", ref="/ui/tak/remoteEntry.js"),
    )
