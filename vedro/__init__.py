import asyncio
from asyncio import CancelledError
from typing import List, Optional

from ._context import context
from ._core import Runner, ScenarioDiscoverer
from ._core._dispatcher import Dispatcher
from ._core._lifecycle import Lifecycle
from ._core._scenario_finder import ScenarioFileFinder
from ._core._scenario_finder._file_filters import AnyFilter, DunderFilter, ExtFilter, HiddenFilter
from ._core._scenario_loader import ScenarioAssertRewriterLoader
from ._interface import Interface
from ._params import params
from ._scenario import Scenario
from ._version import version
from .plugins import Plugin
from .plugins.director import Director, Reporter, RichReporter, SilentReporter
from .plugins.skipper import Skipper, only, skip
from .plugins.terminator import Terminator

__version__ = version
__all__ = ("Scenario", "Interface", "Runner", "run", "only", "skip", "params", "context",)


def run(*, plugins: Optional[List[Plugin]] = None) -> None:
    finder = ScenarioFileFinder(
        file_filter=AnyFilter([
            HiddenFilter(),
            DunderFilter(),
            ExtFilter(only=["py"]),
        ]),
        dir_filter=AnyFilter([
            HiddenFilter(),
            DunderFilter(),
        ])
    )
    loader = ScenarioAssertRewriterLoader()
    discoverer = ScenarioDiscoverer(finder, loader)
    dispatcher = Dispatcher()

    all_plugins = []
    reporters = [
        RichReporter(),
        SilentReporter(),
    ]

    if plugins:
        for plugin in plugins:
            if isinstance(plugin, Reporter):
                reporters.append(plugin)
            else:
                all_plugins.append(plugin)

    all_plugins += [
        Director(reporters),
        Skipper(),
        Terminator(),
    ]

    runner = Runner(dispatcher, (KeyboardInterrupt, SystemExit, CancelledError,))
    lifecycle = Lifecycle(dispatcher, discoverer, runner)
    lifecycle.register_plugins(all_plugins)

    asyncio.run(lifecycle.start())
