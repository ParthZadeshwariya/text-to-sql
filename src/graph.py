from langgraph.graph import StateGraph, END, START
from .state import SQLState
from .nodes import *

def check_for_error(state):
    if state.get("error"):
        return "error"
    else:
        return "success"


def route_to_graph(state):
    if state.get("needs_graph"):
        return "generate"
    else:
        return "skip"
        

def build_graph():
    graph = StateGraph(SQLState)

    graph.add_node("text_to_sql", text_to_sql)
    graph.add_node("execute_query", execute_query)
    graph.add_node("error_solver", error_solver)
    graph.add_node("decide_graph", decide_graph_need)      # New Decision Node
    graph.add_node("generate_graph", generate_visualization) # New Plotting Node
    graph.add_node("analyze_result", analyze_result)

    graph.add_edge(START, "text_to_sql")
    graph.add_edge("text_to_sql", "execute_query")

    # Error Handling Split
    graph.add_conditional_edges(
        "execute_query",
        check_for_error,
        {
            "error": "error_solver",
            "success": "decide_graph"  # If successful, go to decision node
        }
    )

    # Graph Decision Split
    graph.add_conditional_edges(
        "decide_graph",
        route_to_graph,
        {
            "generate": "generate_graph", # If yes, go to plotter
            "skip": "analyze_result"      # If no, skip to analysis
        }
    )

    # Rejoin Paths
    graph.add_edge("generate_graph", "analyze_result")
    graph.add_edge("error_solver", "execute_query")
    graph.add_edge("analyze_result", END)

    return graph.compile()
