"""Descriptions API"""

import logging

from fastapi import APIRouter
from libpvarki.schemas.product import ProductDescription

LOGGER = logging.getLogger(__name__)

router = APIRouter()  # These endpoints are public


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
