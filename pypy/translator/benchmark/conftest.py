import py

def pytest_ignore_collect_path(path):
    return path.basename == "test"
