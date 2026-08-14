from src.synthesis.graph import build_synthesis_graph


def test_fixed_dimensions_do_not_require_an_llm_planning_node():
    graph = build_synthesis_graph().get_graph()

    assert "plan_dimensions" not in graph.nodes
    assert "extract_paper" in graph.nodes
