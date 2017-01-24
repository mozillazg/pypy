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

        # a map from {task : inferred priority}.
        optionality = dict((goal.lstrip('?'), goal.count('?'))
                           for goal in goals)

        # a map from a task to its depedencies.
        task_deps = {}

        def will_do(task):
            priority = optionality[task]
            if priority < 1:
                return True
            return priority == 1 and task not in skip

        # we're going to first consider all tasks that are reachable,
        # regardless of how many ? are found while searching.  We will
        # record two things about the task - what dependencies it has,
        # for easy searching later, and how many ? should appear
        # before the task.  So if A depends on ?C, and C depends on D,
        # D has one ?.
        #
        # some tasks may be considered more than once here - if a
        # later dependency specifies that a task is not optional,
        # we'll not only update its optionality but also reconsider
        # its own dependencies.
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

        # remove any tasks with too-low priority, simple cycles, and
        # deps with too-low priority.
        for task, deps in list(task_deps.iteritems()):
            if not will_do(task):
                del task_deps[task]
            else:
                if task in deps:
                    deps.remove(task)
                for dep in list(deps):
                    if not will_do(dep):
                        deps.remove(dep)

        # now it's a matter of toposorting the tasks over their deps.
        #
        # we could consider using a sort which is stable in the order
        # that deps are declared, at least unless that order isn't
        # consistent.
        plan = []
        seen = set()
        tasks = list(task_deps)
        while tasks:
            remaining = []
            for task in tasks:
                if task_deps[task] - seen:
                    # this task has unsatisfied dependencies
                    remaining.append(task)
                else:
                    plan.append(task)
                    seen.add(task)
            if len(remaining) == len(tasks): # no progress
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
