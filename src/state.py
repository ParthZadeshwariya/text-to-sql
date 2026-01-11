from typing import TypedDict, Literal, Annotated, Optional

class SQLState(TypedDict):
    text: str
    iteration: int
    query: Optional[str]
    query_result: Optional[str]
    error: Optional[str]
    final_answer: Optional[str]
    needs_graph: Optional[bool]
    graph_type: Optional[str]
    visualization: Optional[str]