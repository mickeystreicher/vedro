import asyncio
from typing import Any, Callable, Coroutine, Type, Union

from vedro.core import ConfigType, Dispatcher, Plugin, PluginConfig, ScenarioScheduler
from vedro.events import (
    ArgParsedEvent,
    ArgParseEvent,
    CleanupEvent,
    ConfigLoadedEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
    StartupEvent,
)

from ._scheduler import RepeaterScenarioScheduler

__all__ = ("Repeater", "RepeaterPlugin",)


SleepType = Callable[[float], Coroutine[Any, Any, None]]


class RepeaterPlugin(Plugin):
    def __init__(self, config: Type["Repeater"], *, sleep: SleepType = asyncio.sleep) -> None:
        super().__init__(config)
        self._scheduler_factory = config.scheduler_factory
        self._sleep = sleep
        self._repeats: int = 1
        self._repeats_delay: float = 0.0
        self._global_config: Union[ConfigType, None] = None
        self._scheduler: Union[ScenarioScheduler, None] = None
        self._repeat_scenario_id: Union[str, None] = None

    def subscribe(self, dispatcher: Dispatcher) -> None:
        dispatcher.listen(ConfigLoadedEvent, self.on_config_loaded) \
                  .listen(ArgParseEvent, self.on_arg_parse) \
                  .listen(ArgParsedEvent, self.on_arg_parsed) \
                  .listen(StartupEvent, self.on_startup) \
                  .listen(ScenarioPassedEvent, self.on_scenario_end) \
                  .listen(ScenarioFailedEvent, self.on_scenario_end) \
                  .listen(CleanupEvent, self.on_cleanup)

    def on_config_loaded(self, event: ConfigLoadedEvent) -> None:
        self._global_config = event.config

    def on_arg_parse(self, event: ArgParseEvent) -> None:
        group = event.arg_parser.add_argument_group("Repeater")
        help_message = ("Number of times to repeat scenarios (default: 1). "
                        "The resulting scenario status will be failed if any repeat fail")
        group.add_argument("-N", "--repeats", type=int, default=self._repeats, help=help_message)
        group.add_argument("--repeats-delay", type=float, default=self._repeats_delay,
                           help="Delay in seconds between scenario repeats (default: 0.0s)")

    def on_arg_parsed(self, event: ArgParsedEvent) -> None:
        self._repeats = event.args.repeats
        self._repeats_delay = event.args.repeats_delay

        if self._repeats < 1:
            raise ValueError("--repeats must be >= 1")

        if self._repeats_delay < 0.0:
            raise ValueError("--repeats-delay must be >= 0.0")

        if self._repeats_delay > 0.0 and self._repeats <= 1:
            raise ValueError("--repeats-delay must be used with --repeats > 1")

        if self._repeats <= 1:
            return

        assert self._global_config is not None  # for type checking
        self._global_config.Registry.ScenarioScheduler.register(self._scheduler_factory, self)

    def on_startup(self, event: StartupEvent) -> None:
        self._scheduler = event.scheduler

    async def on_scenario_end(self,
                              event: Union[ScenarioPassedEvent, ScenarioFailedEvent]) -> None:
        if self._repeats <= 1:
            return

        assert isinstance(self._scheduler, RepeaterScenarioScheduler)  # for type checking

        if self._repeat_scenario_id == event.scenario_result.scenario.unique_id:
            return

        self._repeat_scenario_id = event.scenario_result.scenario.unique_id
        for _ in range(self._repeats - 1):
            if self._repeats_delay > 0.0:
                await self._sleep(self._repeats_delay)
            self._scheduler.schedule(event.scenario_result.scenario)

    def on_cleanup(self, event: CleanupEvent) -> None:
        if self._repeats > 1:
            message = f"repeated x{self._repeats}"
            if self._repeats_delay > 0.0:
                message += f" with delay {self._repeats_delay!r}s"
            event.report.add_summary(message)


class Repeater(PluginConfig):
    plugin = RepeaterPlugin
    description = "Repeat scenarios a specified number of times"

    # Scheduler that will be used to create aggregated result for repeated scenarios
    scheduler_factory: Type[ScenarioScheduler] = RepeaterScenarioScheduler
