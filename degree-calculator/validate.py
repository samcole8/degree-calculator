from typing import List, Optional
from pydantic import BaseModel, field_validator, ValidationError

class Assessment(BaseModel):
    name: str
    weight: int
    mark: Optional[float] = None

    @field_validator("weight")
    @classmethod
    def check_weight(cls, v):
        if not (0 <= v <= 100):
            raise ValueError("Weight must be between 0 and 100")
        return v

    @field_validator("mark")
    @classmethod
    def check_mark(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("Mark must be between 0 and 100, or null")
        return v

class Unit(BaseModel):
    name: str
    credits: int
    assessments: List[Assessment]

class Classification(BaseModel):
    name: str
    threshold: float

    @field_validator("threshold")
    @classmethod
    def check_threshold(cls, v):
        if not (0 <= v <= 100):
            raise ValueError("Threshold must be between 0 and 100")
        return v

class ConfigModel(BaseModel):
    units: List[Unit]
    classifications: Optional[List[Classification]] = None

def validate_config(config: dict):
    try:
        validated = ConfigModel(**config)
    except ValidationError as e:
        print("Config file is invalid:")
        for err in e.errors():
            loc = ".".join(str(i) for i in err['loc'])
            msg = err['msg']
            typ = err['type']
            print(f"{loc}: {msg} ({typ})")
        raise e
