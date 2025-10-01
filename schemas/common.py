from pydantic import BaseModel
from typing import Any, Optional


class NoContentResponse(BaseModel):
    meta: Optional[Any] = ""
    data: Optional[Any] = ""
    status: str = "success"
    code: int = 204
    message: str = ""


class UnauthorizedResponse(BaseModel):
    meta: Optional[Any] = ""
    data: Optional[Any] = ""
    status: str = "error"
    code: int = 401
    message: str = "Unauthorized"


class BadRequestResponse(BaseModel):
    meta: Optional[Any] = ""
    data: Optional[Any] = ""
    status: str = "error"
    code: int = 400
    message: str = "Bad Request"


class ForbiddenResponse(BaseModel):
    meta: Optional[Any] = ""
    data: Optional[Any] = ""
    status: str = "error"
    code: int = 403
    message: str = "You don't have permissions to perform this action"


class NotFoundResponse(BaseModel):
    meta: Optional[Any] = ""
    data: Optional[Any] = ""
    status: str = "error"
    code: int = 404
    message: str = "Not found"


class InternalServerErrorResponse(BaseModel):
    meta: Optional[Any] = ""
    data: Optional[Any] = ""
    status: str = "error"
    code: int = 500
    message: str = "Internal Error"


class NotImplementedResponse(BaseModel):
    meta: Optional[Any] = ""
    data: Optional[Any] = ""
    status: str = "error"
    code: int = 501
    message: str = "Not Yet implemented"


class CudResponseSchema(BaseModel):
    meta: Optional[Any] = ""
    data: Optional[dict] = {"message": ""}
    status: str = "success"
    code: int = 201
    message: str = ""