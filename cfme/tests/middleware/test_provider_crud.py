import uuid
import pytest

from utils import testgen
from utils.providers import setup_a_provider as _setup_a_provider
from utils.update import update
from utils.version import current_version

pytestmark = pytest.mark.uncollectif(lambda: current_version() < "5.5")

pytest_generate_tests = testgen.generate(testgen.middleware_providers, scope="function")


@pytest.fixture(scope="function")
def a_middleware_provider():
    return _setup_a_provider("mjddleware")


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_provider_crud(request, provider):
    """ Tests provider add with good credentials

    Metadata:
        test_flag: crud
    """
    provider.create()
    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete(cancel=False)
    provider.wait_for_delete()


def test_provider_edit_port(request, a_middleware_provider):
    old_port = a_middleware_provider.port
    request.addfinalizer(lambda: a_middleware_provider.update({'port': old_port}))
    with update(a_middleware_provider):
        a_middleware_provider.port = '1234'
    assert str(a_middleware_provider.port) == a_middleware_provider.get_detail('Properties', 'Port')
