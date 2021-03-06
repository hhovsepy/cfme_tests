import pytest


@pytest.mark.trylast
def pytest_runtest_teardown(item, nextitem):
    if item.config.getoption('sauce'):
        from cfme.utils.browser import ensure_browser_open, quit, browser
        ensure_browser_open()
        browser().execute_script("sauce:job-name={}".format(item.name))
        quit()
