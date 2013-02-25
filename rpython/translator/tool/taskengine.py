

class SimpleTaskEngine(object):

    def __init__(self):
        self._plan_cache = {}

        self.tasks = tasks = {}

        for name in dir(self):
            if name.startswith('task_'):
                task_name = name[len('task_'):]
                task = getattr(self, name)
                assert callable(task)
                task_deps = getattr(task, 'task_deps', [])

                tasks[task_name] = task, task_deps

    def _execute(self, goals, *args, **kwds):
        res = None
        for goal in goals:
            taskcallable, _ = self.tasks[goal]
            self._event('planned', goal, taskcallable)
        for goal in goals:
            taskcallable, _ = self.tasks[goal]
            self._event('pre', goal, taskcallable)
            try:
                res = self._do(goal, taskcallable, *args, **kwds)
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                self._error(goal)
                raise
            self._event('post', goal, taskcallable)
        return res

    def _do(self, goal, func, *args, **kwds):
        return func()

    def _event(self, kind, goal, func):
        pass
    
    def _error(self, goal):
        pass


        
        
