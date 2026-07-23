import pytest
from pydantic import ValidationError

from app.services.program.regression_graphs import RegressionEdge, RegressionGraphsConfig, get_regression_graphs


def test_real_config_loads_and_covers_every_active_template_pattern():
    graphs = get_regression_graphs()
    for pattern in ("squat", "hinge", "horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull"):
        edges = graphs.patterns[pattern]
        assert sum(1 for e in edges if e.kind == "regression") >= 2
        assert sum(1 for e in edges if e.kind == "cross_pattern") >= 1


def test_get_regression_graphs_is_cached():
    assert get_regression_graphs() is get_regression_graphs()


def test_edge_rejects_unknown_provocation():
    with pytest.raises(ValidationError):
        RegressionEdge(from_slug="a", to="b", kind="regression", relieves=["not_a_real_provocation"])


def test_edge_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        RegressionEdge(from_slug="a", to="b", kind="not_a_real_kind", relieves=["axial_loading"])


def test_config_rejects_unknown_pattern_key():
    edge = RegressionEdge(from_slug="a", to="b", kind="regression", relieves=["axial_loading"])
    with pytest.raises(ValidationError, match="unknown movement pattern"):
        RegressionGraphsConfig(config_version="test", patterns={"not_a_real_pattern": [edge]})


def test_edge_accepts_from_alias_for_yaml_loading():
    edge = RegressionEdge.model_validate({"from": "a", "to": "b", "kind": "regression", "relieves": ["axial_loading"]})
    assert edge.from_slug == "a"
