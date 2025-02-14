from importlib import import_module
from typing import Protocol, runtime_checkable
from .itm_action_handler import ITMActionHandler
from .itm_scenario import ITMScenario
from .itm_scenario_reader import ITMScenarioReader

@runtime_checkable
class ITMDomainConfig(Protocol):
    def get_domain_name(self) -> str:
        ...
    def get_action_handler(self, session) -> ITMActionHandler:
        ...
    def get_action_time_filespec(self) -> str:
        ...
    def get_scenario(self, yaml_path, session, training = False) -> ITMScenario:
        ...
    def get_scenario_reader(self, yaml_path: str) -> ITMScenarioReader:
        ...

class ITMDomainConfigFactory:
    @staticmethod
    def create_domain_factory(domain: str, *args, **kwargs) -> ITMDomainConfig:
        try:
            module = import_module(f"swagger_server.itm.domains.{domain}.{domain}_config")
            klass = getattr(module, f"{domain.capitalize()}Config")
            instance = klass(*args, **kwargs)
            return instance
        except (ImportError, AttributeError, TypeError) as e:
            print(f"Error instantiating '{domain}' domain config from factory: {e}")
            return None
