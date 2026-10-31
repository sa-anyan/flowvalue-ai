"""Original FlowValue parser validation base, decoupled from the legacy costing engine."""
from pydantic import BaseModel,ConfigDict

class Model(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)
