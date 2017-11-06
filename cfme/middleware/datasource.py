import attr

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException
from wrapanapi.hawkular import CanonicalPath

from cfme.common import WidgetasticTaggable, UtilizationMixin
from cfme.exceptions import MiddlewareDatasourceNotFound
from cfme.middleware.provider import (
    MiddlewareBase, download, get_server_name, MiddlewareProvider)
from cfme.middleware.provider import parse_properties
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.provider.middleware_views import (DatasourceDetailsView,
                                                       DatasourceAllView)
from cfme.middleware.server import MiddlewareServer
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils import attributize_string
from cfme.utils.appliance import Navigatable, current_appliance
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.providers import get_crud_by_name, list_providers_by_class
from cfme.utils.varmeth import variable


def _db_select_query(name=None, nativeid=None, appliance=None):
    """Column order: `id`, `nativeid`, `name`, `properties`, `server_name`,
    `feed`, `provider_name`, `ems_ref`, `hostname`"""
    t_ms = current_appliance.db.client['middleware_servers']
    t_mds = current_appliance.db.client['middleware_datasources']
    t_ems = current_appliance.db.client['ext_management_systems']
    query = current_appliance.db.client.session.query(
        t_mds.id,
        t_mds.nativeid,
        t_mds.name,
        t_mds.properties,
        t_ms.name.label('server_name'),
        t_ms.feed,
        t_ems.name.label('provider_name'),
        t_ms.hostname,
        t_mds.ems_ref)\
        .join(t_ms, t_mds.server_id == t_ms.id).join(t_ems, t_mds.ems_id == t_ems.id)
    if name:
        query = query.filter(t_mds.name == name)
    if nativeid:
        query = query.filter(t_mds.nativeid == nativeid)
    if appliance and isinstance(appliance, MiddlewareServer):
        query = query.filter(t_ms.name == appliance.name)
        if appliance.feed:
            query = query.filter(t_ms.feed == appliance.feed)
    if appliance and isinstance(appliance, MiddlewareProvider):
        query = query.filter(t_ems.name == appliance.name)
    return query


def _get_datasources_page(appliance=None):
    if appliance and isinstance(appliance, MiddlewareServer):
        # if server instance is provided navigate through server page
        return navigate_to(appliance, 'ServerDatasources')
    elif appliance and isinstance(appliance, MiddlewareProvider):
        # if provider instance is provided navigate through provider page
        return navigate_to(appliance, 'ProviderDatasources')
    else:  # if None(provider and server) given navigate through all middleware datasources page
        return navigate_to(MiddlewareDatasource, 'All')


@attr.s
class MiddlewareDatasource(BaseEntity, MiddlewareBase, WidgetasticTaggable, Navigatable, UtilizationMixin):
    """
    Model of Middleware Datasource in cfme.

    Args:
        name: Name of the datasource
        server: Server object of the datasource (MiddlewareServer)
        provider: Provider object (HawkularProvider)
        nativeid: Native id (internal id) of datasource
        properties: Datasource driver name, connection URL and JNDI name
        db_id: database row id of datasource
    """
    property_tuples = [('name', 'Name'), ('nativeid', 'Nativeid'),
                       ('driver_name', 'Driver Name'), ('jndi_name', 'JNDI Name'),
                       ('connection_url', 'Connection URL'), ('enabled', 'Enabled')]
    taggable_type = 'MiddlewareDatasource'

    pretty_attrs = ['name', 'server', 'provider', 'nativeid', 'hostname', 'properties', 'db_id']

    name = attr.ib()
    server = attr.ib()
    provider = attr.ib(default=None)
    nativeid = attr.ib(default=None)
    hostname = attr.ib(default=None)
    properties = attr.ib(default={})
    db_id = attr.ib(default=None)

    def __attrs_post_init__(self):
        for property in self.properties:
            setattr(self, attributize_string(property), self.properties[property])

    @classmethod
    def datasources(cls, provider=None, server=None):
        datasources = []
        view = _get_datasources_page(provider=provider, server=server)
        for _ in view.entities.paginator.pages():
            for row in view.entities.elements:
                _server = MiddlewareServer(provider=provider, name=row.server.text)
                datasources.append(MiddlewareDatasource(
                    provider=provider,
                    server=_server,
                    name=row.datasource_name.text,
                    hostname=row.host_name.text))
        return datasources

    @classmethod
    def datasources_in_db(cls, server=None, provider=None, strict=True):
        datasources = []
        rows = _db_select_query(server=server, provider=provider).all()
        _provider = provider
        for datasource in rows:
            if strict:
                _provider = get_crud_by_name(datasource.provider_name)
            _server = MiddlewareServer(
                name=datasource.server_name,
                feed=datasource.feed,
                provider=provider)
            datasources.append(MiddlewareDatasource(
                nativeid=datasource.nativeid,
                name=datasource.name,
                db_id=datasource.id,
                server=_server,
                provider=_provider,
                hostname=datasource.hostname,
                properties=parse_properties(datasource.properties)))
        return datasources

    @classmethod
    def _datasources_in_mgmt(cls, provider, server=None):
        datasources = []
        rows = provider.mgmt.inventory.list_server_datasource()
        for datasource in rows:
            _server = MiddlewareServer(name=get_server_name(datasource.path),
                                       feed=datasource.path.feed_id,
                                       provider=provider)
            _include = False
            if server:
                if server.name == _server.name:
                    _include = True if not server.feed else server.feed == _server.feed
            else:
                _include = True
            if _include:
                datasources.append(MiddlewareDatasource(nativeid=datasource.id,
                                                        name=datasource.name,
                                                        server=_server,
                                                        provider=provider))
        return datasources

    @classmethod
    def datasources_in_mgmt(cls, provider=None, server=None):
        if provider is None:
            datasources = []
            for _provider in list_providers_by_class(HawkularProvider):
                datasources.extend(cls._datasources_in_mgmt(_provider, server))
            return datasources
        else:
            return cls._datasources_in_mgmt(provider, server)

    @classmethod
    def remove_from_list(cls, datasource):
        view = _get_datasources_page(server=datasource.server)
        view.entities.get_item(by_name=datasource.name).check()
        view.toolbar.configuration.item_select('Remove', handle_alert=True)
        view.flash.assert_success_message('The selected datasources were removed')

    def load_details(self, refresh=False):
        view = navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_dsource = self.datasource(method='db')
            self.db_id = tmp_dsource.db_id
        if refresh:
            view.browser.selenium.refresh()
            view.flush_widget_cache()
        return view

    @variable(alias='ui')
    def datasource(self):
        self.load_details(refresh=False)
        self.id = self.get_detail("Properties", "Nativeid")
        self.server = MiddlewareServer(
            provider=self.provider,
            name=self.get_detail("Relationships", "Middleware Server"))
        return self

    @datasource.variant('mgmt')
    def datasource_in_mgmt(self):
        db_ds = _db_select_query(name=self.name, server=self.server,
                                 nativeid=self.nativeid).first()
        if db_ds:
            path = CanonicalPath(db_ds.ems_ref)
            mgmt_ds = self.provider.mgmt.inventory.get_config_data(feed_id=path.feed_id,
                                                                   resource_id=path.resource_id)
            if mgmt_ds:
                ds = MiddlewareDatasource(
                    server=self.server,
                    provider=self.provider,
                    name=db_ds.name,
                    hostname=db_ds.hostname,
                    nativeid=db_ds.nativeid,
                    properties=mgmt_ds.value)
                return ds
        return None

    @datasource.variant('db')
    def datasource_in_db(self):
        datasource = _db_select_query(name=self.name, server=self.server,
                                      nativeid=self.nativeid).first()
        if datasource:
            _server = MiddlewareServer(name=datasource.server_name, provider=self.provider)
            return MiddlewareDatasource(
                provider=self.provider,
                server=_server,
                db_id=datasource.id,
                nativeid=datasource.nativeid,
                name=datasource.name,
                hostname=datasource.hostname,
                properties=parse_properties(datasource.properties))
        return None

    @datasource.variant('rest')
    def datasource_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')

    @classmethod
    def download(cls, extension, provider=None, server=None):
        view = _get_datasources_page(provider, server)
        download(view, extension)

    def delete(self, cancel=False):
        """
        Deletes a datasource from CFME

        :param cancel: Whether to cancel the deletion, defaults to False
        """
        view = self.load_details()
        view.toolbar.configuration.item_select('Remove', handle_alert=not cancel)

        # flash message only displayed if it was deleted
        if not cancel:
            view.flash.assert_success_message('The selected datasources were removed')


@attr.s
class DatasourceCollection(BaseCollection):
    """Collection class for `cfme.middleware.datasource.MiddlewareDatasource`"""
    ENTITY = MiddlewareDatasource

    def __init__(self, appliance, parent):
        self.appliance = appliance
        self.parent = parent

    def all(self):
        """Return all Datasources of the appliance in CFME UI.

        Returns: a :py:class:`list`
            of :py:class:`cfme.middleware.datasource.DatastoreCollection` instances
        """
        datasources = []
        view = _get_datasources_page(appliance=self.appliance)
        provider = (self.appliance if isinstance(self.appliance, MiddlewareProvider)
                    else self.appliance.parent)
        for entity in view.entities.get_all(surf_pages=True):
            server = MiddlewareServer(provider=provider, name=entity.server.text)
            datasources.append(self.instantiate(
                self.appliance,
                entity.datasource_name.text,
                provider,
                server,
                None,
                entity.host_name.text))
        return datasources

    def headers(self):
        view = _get_datasources_page(appliance=self.appliance)
        if view.jdr_reports.entities:
            headers = [hdr.encode("utf-8")
                       for hdr in view.entities.elements.headers if hdr]
        return headers

    def all_in_db(self):
        """Return all Datasources of the appliance in CFME DB.

        Returns: a :py:class:`list`
            of :py:class:`cfme.middleware.datasource.DatastoreCollection` instances
        """
        datasources = []
        rows = _db_select_query(appliance=self.appliance).all()
        provider = (self.appliance if isinstance(self.appliance, MiddlewareProvider)
                    else self.appliance.parent)
        for datasource in rows:
            server = MiddlewareServer(
                name=datasource.server_name,
                feed=datasource.feed,
                provider=provider)
            datasources.append(self.instantiate(
                self.appliance,
                datasource.name,
                server,
                provider,
                datasource.nativeid,
                datasource.hostname,
                parse_properties(datasource.properties),
                datasource.id))
        return datasources

    def all_in_mgmt(self):
        """Return all Datasources of the appliance in Middleware Provider MGMT API.

        Returns: a :py:class:`list`
            of :py:class:`cfme.middleware.datasource.DatastoreCollection` instances
        """
        datasources = []
        provider = (self.appliance if isinstance(self.appliance, MiddlewareProvider)
                    else self.appliance.parent)
        rows = provider.mgmt.inventory.list_server_datasource()
        for datasource in rows:
            server = MiddlewareServer(
                name=get_server_name(datasource.path),
                feed=datasource.path.feed_id,
                provider=provider)
            datasources.append(self.instantiate(
                self.appliance,
                datasource.name,
                server,
                provider,
                datasource.id))
        return datasources


@navigator.register(DatasourceCollection, 'All')
class All(CFMENavigateStep):
    VIEW = DatasourceAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Middleware', 'Datasources')

    def resetter(self):
        """Reset view and selection"""
        self.view.entities.paginator.check_all()
        self.view.entities.paginator.uncheck_all()


@navigator.register(MiddlewareDatasource, 'Details')
class Details(CFMENavigateStep):
    VIEW = DatasourceDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        try:
            if self.obj.server:
                # TODO find_row_on_pages change to entities.get_entity()
                row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.elements,
                    datasource_name=self.obj.name,
                    server=self.obj.server.name)
            else:
                row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.elements,
                    datasource_name=self.obj.name)
        except NoSuchElementException:
            raise MiddlewareDatasourceNotFound(
                "Datasource '{}' not found in table".format(self.obj.name))
        row.click()
