import click

from pype import plug
from pype import asynch
from pype import interpret

registry = plug.Registry()


def calculate_function(traversal, autocall=None):
    if autocall is None:
        autocall = traversal.global_invocation_options.global_options["autocall"]

    return {
        "function": interpret.build_function(
            traversal.specific_invocation_params["command"],
            traversal.global_invocation_options.global_options["global_namespace"],
            autocall,
        )
    }


@registry.add_traversal("map", calculate_more_params=calculate_function)
async def map(function, items, stack, max_concurrent):
    return await stack.enter_async_context(
        asynch.async_map(function, items, max_concurrent)
    )


@registry.add_traversal("filter", calculate_more_params=calculate_function)
async def filter(function, items, stack, max_concurrent):
    return await stack.enter_async_context(
        asynch.async_filter(function, items, max_concurrent)
    )


@registry.add_traversal("apply", calculate_more_params=calculate_function)
async def apply(function, items):
    return asynch.AsyncIterableWrapper([await function([x async for x in items])])


@registry.add_traversal(
    "eval", calculate_more_params=lambda x: calculate_function(x, autocall=False)
)
async def eval(function):
    return asynch.AsyncIterableWrapper([await function(None)])


@registry.add_traversal("stack", calculate_more_params=calculate_function)
async def stack(function, items):
    return asynch.AsyncIterableWrapper(
        [await function("".join([x + "\n" async for x in items]))]
    )


subcommands = [
    click.Command("map", short_help="Call <command> on each line of input."),
    click.Command("apply", short_help="Call <command> on input as a sequence."),
    click.Command(
        "filter",
        short_help="Call <command> on each line of input and exclude false values.",
    ),
    click.Command("eval", short_help="Call <command> without any input."),
    click.Command(
        "stack", short_help="Call <command> on input as a single concatenated string."
    ),
]


def build_callback(sub_command):
    def callback(command):
        return [{"name": sub_command.name, "command": command}]

    return callback


for subcommand in subcommands:
    subcommand.params = [click.Argument(["command"])]
    subcommand.callback = build_callback(subcommand)
    # TODO: add_cli and add_traversal should be the non-decorator form
    registry.add_cli(name=subcommand.name)(subcommand)