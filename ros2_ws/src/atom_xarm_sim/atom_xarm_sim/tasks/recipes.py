"""Task composition independent of ROS: tasks select existing capabilities."""
from dataclasses import dataclass
from typing import Callable, Mapping

OBSERVATION = ('prepare_observation', 'move_observation', 'capture_observation')
RECIPES = {
    'visual_observe': OBSERVATION,
    'visual_approach': OBSERVATION + ('prepare_approach', 'align_selected', 'approach_selected'),
}
CAPABILITY_STEPS = tuple(dict.fromkeys(step for recipe in RECIPES.values() for step in recipe))

@dataclass(frozen=True)
class StepResult:
    name: str
    completed: bool


def execute_recipe(name: str, capabilities: Mapping[str, Callable], on_step=None, on_complete=None):
    """Validate the entire recipe before motion; abort on first capability error."""
    if name not in RECIPES:
        raise ValueError(f'Unknown task recipe: {name}')
    recipe = RECIPES[name]
    missing = [step for step in recipe if not callable(capabilities.get(step))]
    if missing:
        raise ValueError(f'Missing task capabilities: {missing}')
    results = []
    for step in recipe:
        if on_step:
            on_step(step)
        capabilities[step]()
        results.append(StepResult(step, True))
        if on_complete:
            on_complete(step)
    return tuple(results)
