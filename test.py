from pydantic import BaseModel
from typing import Dict, Any


class Blog(BaseModel):
    name: str

    # _model: Type[DeclarativeBase]
    _secret_value: str = "Abbey"
    _table_columns: Dict[str, Any] = {}


b = Blog(name="abbey")
print(b._table_columns)
