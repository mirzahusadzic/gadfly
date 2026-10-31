"""Work counted, not timed: the Python instructions a call executes, so a
guard can tell linear growth from quadratic without a clock."""

import sys


def instructions(call) -> int:
    """How many bytecode instructions `call()` executes."""
    monitoring, tool = sys.monitoring, 3  # 3 is a free tool id: not debugger, coverage or profiler
    count = 0

    def counted(code, offset):
        nonlocal count
        count += 1

    monitoring.use_tool_id(tool, "midwife-tests")
    try:
        monitoring.register_callback(tool, monitoring.events.INSTRUCTION, counted)
        monitoring.set_events(tool, monitoring.events.INSTRUCTION)
        call()
    finally:
        monitoring.set_events(tool, 0)
        monitoring.register_callback(tool, monitoring.events.INSTRUCTION, None)
        monitoring.free_tool_id(tool)
    return count
