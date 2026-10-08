from pydantic_ai.agent import Agent, AgentRetries
from pydantic_ai.models import Model

from schema_extractor.schema.meta_models import TemplateSpec

INSTRUCTIONS = """\
Jesteś asystentem, który na podstawie opisu użytkownika w języku naturalnym \
tworzy specyfikację szablonu do ekstrakcji danych z dokumentów.

Zasady tworzenia specyfikacji:
    - Nazwa szablonu (`name`) oraz nazwy pól (`FieldDefinition.name`) muszą być \
    poprawnymi identyfikatorami Pythona w snake_case (np. `invoice_number`, \
    nie `Invoice Number` ani `numer-faktury`). Nazwy pól nie mogą zaczynać się \
    od `_` ani `model_` i nie mogą być nazwami typowych metod obiektów \
    (np. `schema`, `copy`, `json`).
    - Każde pole musi mieć jasny, jednoznaczny `description` - będzie on \
    jedynym kontekstem dla innego modelu, który później faktycznie wyciągnie \
    wartość z dokumentu, więc nie może być ogólnikowy.
    - Ustaw `required=False` tylko dla pól, które w typowym dokumencie tego \
    rodzaju mogą realnie nie występować.
    - Dodawaj wyłącznie pola, o które prosi użytkownik. Nie dodawaj pól \
    dodatkowych, nawet jeśli są oczywistym elementem tego typu dokumentu, \
    chyba że użytkownik wprost poprosi o zasugerowanie dodatkowych pól.

Zasady poprawiania:
    - Gdy dostajesz aktualną specyfikację razem z uwagami użytkownika, \
    zwróć ją w pełnej, poprawionej postaci.
    - Zmieniaj wyłącznie to, o co użytkownik prosi. Pozostałe pola oraz \
    nazwę szablonu zachowaj bez zmian.
"""


def build_schema_agent(model: Model) -> Agent[None, TemplateSpec]:
    retries: AgentRetries = {"output": 3}
    return Agent(
        model, output_type=TemplateSpec, retries=retries, instructions=INSTRUCTIONS
    )


def build_refine_prompt(current: TemplateSpec, feedback: str) -> str:
    return (
        "Aktualna specyfikacja szablonu:\n"
        f"<aktualna_specyfikacja>\n{current.model_dump_json(indent=2)}\n</aktualna_specyfikacja>\n\n"
        "Uwagi użytkownika:\n"
        f"<uwagi_uzytkownika>\n{feedback}\n</uwagi_uzytkownika>\n\n"
        "Zwróć pełną, poprawioną specyfikację."
    )


async def generate_template_spec(
    user_prompt: str, *, agent: Agent[None, TemplateSpec]
) -> TemplateSpec:
    result = await agent.run(user_prompt)
    return result.output


async def refine_template_spec(
    current: TemplateSpec, feedback: str, *, agent: Agent[None, TemplateSpec]
) -> TemplateSpec:
    result = await agent.run(build_refine_prompt(current, feedback))
    return result.output