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

        plan = []
        goal_walker = goals[::-1]
        flattened_goals = []
        for base_goal in goals[::-1]:
            goal_walker = [base_goal]
            dep_walker = [iter(self.tasks[base_goal.lstrip('?')][1])]
            while goal_walker:
                for subgoal in dep_walker[-1]:
                    break
                else:
                    # all dependencies are in flattened_goals. record
                    # this goal.
                    dep_walker.pop()
                    goal = goal_walker.pop()
                    if goal not in flattened_goals:
                        flattened_goals.append(goal)
                    continue
                if subgoal in goal_walker:
                    raise RuntimeException('circular dependency')

                # subgoal must be at least as optional as its parent
                qs = goal_walker[-1].count('?')
                if subgoal.count('?') < qs:
                    subgoal = '?' * qs + subgoal.lstrip('?')

                # we'll add this goal once we have its dependencies.
                goal_walker.append(subgoal)
                dep_walker.append(iter(self.tasks[subgoal.lstrip('?')][1]))

        plan = []
        for name in flattened_goals:
            name = name.lstrip('?')
            if name in plan:
                continue
            will_run = name in flattened_goals or (
                        '?' + name in flattened_goals and name not in skip)
            if will_run:
                plan.append(name)
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
