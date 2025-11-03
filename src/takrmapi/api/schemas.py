from typing import List
from pydantic import BaseModel, Field

class TakZipFile(BaseModel):
    title: str = Field(..., description="Original filename or title of the zip file.")
    filename: str = Field(..., description="Filename used for download, includes user callsign.")
    data: str = Field(
        ...,
        description="Base64-encoded zip file contents",
        example="data:application/zip;base64,UEsDBBQAAAAI..."
    )

class ClientInstructionData(BaseModel):
    tak_zips: List[TakZipFile] = Field(..., description="List of packaged mission zip files.")

class ClientInstructionResponse(BaseModel):
    data: ClientInstructionData = Field(..., description="Container object for returned data.")