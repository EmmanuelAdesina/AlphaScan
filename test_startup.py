import time
from fastapi.testclient import TestClient
from api.routes import app
from api.dependencies import get_engine

if __name__ == '__main__':
    print('Starting TestClient context...')
    with TestClient(app) as client:
        print('startup done')
        engine = get_engine()
        print('engine.running=', engine.state.running)
        print('engine.cycle=', engine.state.cycle)
        print('engine.total_scans=', engine.state.total_scans)
        print('task_exists=', hasattr(app.state, 'engine_task'))
        task = getattr(app.state, 'engine_task', None)
        print('task', task)
        if task:
            time.sleep(2)
            print('after_sleep_engine.running=', engine.state.running)
            print('after_sleep_cycle=', engine.state.cycle)
            print('after_sleep_total_scans=', engine.state.total_scans)
    print('shutdown done')
