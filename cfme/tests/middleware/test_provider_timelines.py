import pytest
from datetime import datetime

from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for
from datasource_methods import (
    ORACLE_12C_DS,
    generate_ds_name,
    delete_datasource_from_list
)
from deployment_methods import (
    RESOURCE_EAR_NAME,
    RESOURCE_WAR_NAME,
    check_deployment_appears,
    check_deployment_not_listed,
    deploy_archive,
    generate_runtime_name,
    undeploy,
    get_resource_path
)
from jdbc_driver_methods import download_jdbc_driver, deploy_jdbc_driver
from server_methods import (
    get_eap_server,
    verify_server_suspended,
    get_domain_server
)


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
    pytest.mark.provider([HawkularProvider], scope="function"),
]

DEPLOYMENT_OK_EVENT = 'hawkular_deployment.ok'
UNDEPLOYMENT_OK_EVENT = 'hawkular_deployment_remove.ok'
DEPLOYMENT_FAIL_EVENT = 'hawkular_deployment.error'
DS_CREATION_OK_EVENT = 'hawkular_datasource.ok'
DS_DELETION_OK_EVENT = 'hawkular_datasource_remove.ok'
SERVER_RELOAD_OK_EVENT = 'hawkular_server_reload.ok'
SERVER_RESTART_OK_EVENT = 'hawkular_server_restart.ok'
SERVER_SUSPEND_OK_EVENT = 'hawkular_server_suspend.ok'
SERVER_RESUME_OK_EVENT = 'hawkular_server_resume.ok'
SERVER_GROUP_RELOAD_OK_EVENT = 'hawkular_server_group_reload.ok'
SERVER_GROUP_RESTART_OK_EVENT = 'hawkular_server_group_restart.ok'
SERVER_GROUP_SUSPEND_OK_EVENT = 'hawkular_server_group_suspend.ok'
SERVER_GROUP_RESUME_OK_EVENT = 'hawkular_server_group_resume.ok'


@pytest.yield_fixture(scope="function")
def server(provider):
    server = get_eap_server(provider)
    yield server
    server.restart_server()


@pytest.yield_fixture(scope="function")
def domain_server(provider):
    server = get_domain_server(provider)
    yield server
    # make sure server is resumed just in case, if after test server is suspended
    server.resume_server()
    # resume does not start stopped server
    # make sure server is started after test execution
    server.start_server()


def test_load_deployment_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_deploy_events(provider)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, DEPLOYMENT_OK_EVENT)


def test_undeployment_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_undeploy_events(provider)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, UNDEPLOYMENT_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, UNDEPLOYMENT_OK_EVENT)


def test_deployment_failure_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_deploy_fail_events(provider)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_FAIL_EVENT)
    load_event_summary(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_FAIL_EVENT)


def test_create_datasource_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_ds_creation_events(provider, ORACLE_12C_DS)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DS_CREATION_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, DS_CREATION_OK_EVENT)


def test_delete_dataource_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_ds_deletion_events(provider, ORACLE_12C_DS)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DS_DELETION_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, DS_DELETION_OK_EVENT)


def test_server_reload_timelines(provider, server):
    """Tests server reload operation events on Timelines
    """
    before_test_date = datetime.utcnow()
    gen_server_reload_events(server)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, SERVER_RELOAD_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, SERVER_RELOAD_OK_EVENT)


def test_server_restart_timelines(provider, server):
    """Tests server restart operation events on Timelines
    """
    before_test_date = datetime.utcnow()
    gen_server_restart_events(server)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, SERVER_RESTART_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, SERVER_RESTART_OK_EVENT)


def test_server_suspend_resume_timelines(provider, server):
    """Tests server restart operation events on Timelines
    """
    before_test_date = datetime.utcnow()
    gen_server_suspend_resume_events(provider, server)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, SERVER_SUSPEND_OK_EVENT)
    check_contains_event(timelines, before_test_date, SERVER_RESUME_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, SERVER_SUSPEND_OK_EVENT)
    check_not_contains_event(timelines, before_test_date, SERVER_RESUME_OK_EVENT)


def test_domain_server_reload_timelines(provider, domain_server):
    """Tests domain_server reload operation events on Timelines
    """
    before_test_date = datetime.utcnow()
    gen_server_reload_events(domain_server)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, SERVER_RELOAD_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, SERVER_RELOAD_OK_EVENT)


def test_domain_server_restart_timelines(provider, domain_server):
    """Tests server restart operation events on Timelines
    """
    before_test_date = datetime.utcnow()
    gen_server_restart_events(domain_server)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, SERVER_RESTART_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, SERVER_RESTART_OK_EVENT)


def test_domain_server_suspend_resume_timelines(provider, domain_server):
    """Tests server restart operation events on Timelines
    """
    before_test_date = datetime.utcnow()
    gen_server_suspend_resume_events(provider, domain_server)
    timelines = navigate_to(provider, 'Timelines')
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, SERVER_SUSPEND_OK_EVENT)
    check_contains_event(timelines, before_test_date, SERVER_RESUME_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, SERVER_SUSPEND_OK_EVENT)
    check_not_contains_event(timelines, before_test_date, SERVER_RESUME_OK_EVENT)


def load_event_details(timelines):
    timelines.filter.time_range.select_by_visible_text('Days')
    timelines.filter.event_category.select_by_visible_text('Application')
    timelines.filter.detailed_events.fill(True)
    timelines.filter.apply.click()


def load_event_summary(timelines):
    timelines.filter.detailed_events.fill(False)
    timelines.filter.apply.click()


def check_contains_event(timelines, before_test_date, event):
    wait_for(lambda: contains_event(timelines, event, before_test_date),
        fail_func=timelines.filter.apply.click, delay=10, num_sec=60,
        message='Event {} must be listed in Timelines.'.format(event))


def check_not_contains_event(timelines, before_test_date, event):
    wait_for(lambda: not contains_event(timelines, event, before_test_date),
        fail_func=timelines.filter.apply.click, delay=10, num_sec=60,
        message='Event {} must NOT be listed in Timelines.'.format(event))


def contains_event(timelines, event_type, date_after=datetime.min):
    """Checks whether list of events contains provided particular
    'event_type' with data not earlier than provided 'date_after'.
    If 'date_after' is not provided, will use datetime.min.
    """
    if date_after and not isinstance(date_after, datetime):
        raise KeyError("'date_after' should be an instance of date")
    for event in timelines.chart.get_events():
        if event.event_type == event_type and datetime.strptime(
                event.date_time, '%Y-%m-%d %H:%M:%S %Z') >= date_after:
            return True
    return False


def gen_deploy_events(provider):
    server = get_eap_server(provider)
    file_path = get_resource_path(RESOURCE_WAR_NAME)
    runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name)
    return runtime_name


def gen_undeploy_events(provider):
    server = get_eap_server(provider)
    runtime_name = gen_deploy_events(provider)
    check_deployment_appears(provider, server, runtime_name)
    undeploy(provider, server, runtime_name)
    check_deployment_not_listed(provider, server, runtime_name)
    return runtime_name


def gen_deploy_fail_events(provider):
    server = get_eap_server(provider)
    file_path = get_resource_path(RESOURCE_EAR_NAME)
    runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name)
    runtime_name2 = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name2, overwrite=True)
    return runtime_name


def gen_ds_creation_events(provider, datasource):
    server = get_eap_server(provider)
    ds_name = generate_ds_name(datasource.datasource_name)
    jndi_name = generate_ds_name(datasource.jndi_name)
    file_path = download_jdbc_driver(datasource.driver.database_name)
    deploy_jdbc_driver(provider, server, file_path,
                       driver_name=datasource.driver.driver_name,
                       module_name=datasource.driver.module_name,
                       driver_class=datasource.driver.driver_class,
                       major_version=datasource.driver.major_version,
                       minor_version=datasource.driver.minor_version)
    server.add_datasource(ds_type=datasource.database_type,
                          ds_name=ds_name,
                          jndi_name=jndi_name,
                          driver_name=datasource.driver.driver_name,
                          driver_module_name=datasource.driver.module_name,
                          driver_class=datasource.driver.driver_class,
                          ds_url=datasource.connection_url.replace("\\", ""),
                          username=datasource.username,
                          password=datasource.password)
    ds_name = "Datasource [{}]".format(ds_name)
    return ds_name


def gen_ds_deletion_events(provider, datasource_params):
    datasource_name = gen_ds_creation_events(provider, datasource_params)
    delete_datasource(provider, datasource_name)
    return datasource_name


def gen_server_reload_events(server):
    server.reload_server()


def gen_server_restart_events(server):
    server.restart_server()


def gen_server_suspend_resume_events(provider, server):
    server.suspend_server()
    verify_server_suspended(provider, server)
    server.resume_server()


def delete_datasource(provider, datasource_name):
    delete_datasource_from_list(provider, datasource_name)
