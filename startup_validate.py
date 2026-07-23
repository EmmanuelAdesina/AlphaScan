import asyncio
import inspect
from api.routes import app
from api.dependencies import get_engine

async def run_startup_handlers():
    for handler in app.router.on_startup:
        print('running startup handler', handler)
        if inspect.iscoroutinefunction(handler):
            await handler()
        else:
            handler()

async def main():
    print('has_startup_handlers=', app.router.on_startup)
    await run_startup_handlers()
    engine = get_engine()
    print('engine id', id(engine))
    print('engine.running=', engine.state.running)
    print('engine.cycle=', engine.state.cycle)
    print('engine.total_scans=', engine.state.total_scans)
    print('task_exists=', hasattr(app.state, 'engine_task'))
    task = getattr(app.state, 'engine_task', None)
    print('task', task)
    if task:
        await asyncio.sleep(2)
        print('after_sleep_engine.running=', engine.state.running)
        print('after_sleep_cycle=', engine.state.cycle)
        print('after_sleep_total_scans=', engine.state.total_scans)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print('task cancelled')

asyncio.run(main())
