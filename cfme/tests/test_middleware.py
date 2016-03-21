import pytest
import time
from utils.browser import ensure_browser_open, quit
from cfme.login import login_admin
from cfme.fixtures import pytest_selenium as sel

@pytest.fixture
def webDriver(request):
    ensure_browser_open()
    login_admin()
 
    def closeSession():
        """ Close Browser """
    request.addfinalizer(closeSession)

    return 


""" Test Case """

def test_simpleMIQ():
    sel.force_navigate('middleware')
    time.sleep(15)
