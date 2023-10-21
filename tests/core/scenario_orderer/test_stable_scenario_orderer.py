import pytest
from baby_steps import given, then, when

from vedro.core.scenario_orderer import StableScenarioOrderer

from ._utils import make_vscenario


@pytest.fixture()
def orderer() -> StableScenarioOrderer:
    return StableScenarioOrderer()


async def test_sort_no_scenarios(*, orderer: StableScenarioOrderer):
    with given:
        scenarios = []

    with when:
        res = await orderer.sort(scenarios)

    with then:
        assert res == []
        assert scenarios == []


async def test_sort_scenarios(*, orderer: StableScenarioOrderer):
    with given:
        orig_scenarios = {path: make_vscenario(path) for path in [
            "scenarios/directory/scn.py",
            "scenarios/dir1/scn1.py",
            "scenarios/dir1/scn2.py",
            "scenarios/dir2/scn2.py",
            "scenarios/scn2.py",
            "scenarios/scn10.py",
        ]}
        scenarios = list(orig_scenarios.values())

    with when:
        res = await orderer.sort(scenarios)

    with then:
        assert res == [
            orig_scenarios["scenarios/scn2.py"],
            orig_scenarios["scenarios/scn10.py"],
            orig_scenarios["scenarios/dir1/scn1.py"],
            orig_scenarios["scenarios/dir1/scn2.py"],
            orig_scenarios["scenarios/dir2/scn2.py"],
            orig_scenarios["scenarios/directory/scn.py"],
        ]
        assert scenarios == list(orig_scenarios.values())
