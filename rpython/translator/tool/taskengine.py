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

    def _plan(self, goals, skip=()):
        skip = [toskip for toskip in skip if toskip not in goals]

        key = (tuple(goals), tuple(skip))
        try:
            return self._plan_cache[key]
        except KeyError:
            pass

        optionality = dict((goal.lstrip('?'), goal.count('?'))
                           for goal in goals)
        task_deps = {}

        def will_do(task):
            priority = optionality[task]
            if priority < 1:
                return True
            return priority == 1 and task not in skip

        goal_walker = list(goals[::-1])
        while goal_walker:
            goal = goal_walker.pop()
            qs = optionality.get(goal, 0)
            if goal not in task_deps:
                task_deps[goal] = deps = set()
                for dep in self.tasks[goal][1]:
                    deps.add(dep.lstrip('?'))
            for dep in self.tasks[goal][1]:
                depname = dep.lstrip('?')
                def_optionality = optionality.get(depname, 5)
                dep_qs = max(qs, dep.count('?'))
                if dep_qs < def_optionality:
                    optionality[depname] = dep_qs
                    goal_walker.append(depname)

        for task, deps in list(task_deps.iteritems()):
            if not will_do(task):
                del task_deps[task]
            else:
                if task in deps:
                    deps.remove(task)
                for dep in list(deps):
                    if not will_do(dep):
                        deps.remove(dep)

        plan = []
        seen = set()
        tasks = list(task_deps)
        while tasks:
            remaining = []
            for task in tasks:
                if task_deps[task] - seen:
                    remaining.append(task)
                else:
                    plan.append(task)
                    seen.add(task)
            if len(remaining) == len(tasks):
                raise RuntimeException('circular dependency')
            tasks = remaining

        self._plan_cache[key] = plan
        return plan

    def _depending_on(self, goal):
        l = []
        for task_name, (task, task_deps) in self.tasks.iteritems():
            if goal in task_deps:
                l.append(task_name)
        return l

    def _depending_on_closure(self, goal):
        d = {}

        def track(goal):
            if goal in d:
                return
            d[goal] = True
            for depending in self._depending_on(goal):
                track(depending)
        track(goal)
        return d.keys()

    def _execute(self, goals, *args, **kwds):
        task_skip = kwds.get('task_skip', [])
        res = None
        goals = self._plan(goals, skip=task_skip)
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
