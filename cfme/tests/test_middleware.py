import pytest
import time
from utils.browser import ensure_browser_open, quit
from cfme.login import login_admin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav
import cfme.web_ui.flash as flash
from cfme.web_ui import Quadicon, Region, listaccordion as list_acc, paginator, toolbar as tb
from cfme.web_ui import Form, Select, fill, form_buttons, paginator, AngularSelect, Table
from cfme.web_ui import Input
from functools import partial
from utils import testgen, version, deferred_verpick

cfg_btn = partial(tb.select, 'Configuration')
add_button = form_buttons.FormButton("Add this Middleware Manager")
save_button = form_buttons.FormButton("Save Changes")
providers_table = Table("//div[@id='main_div']//table")

nav.add_branch('middleware_providers',
               {'middleware_provider_new': lambda _: cfg_btn('Add a New Middleware Provider') })

properties_form = Form(
    fields=[
        ('type_select', {version.LOWEST: Select('select#server_emstype'),
            '5.5': AngularSelect("server_emstype")}),
        ('name_text', Input("name")),
        ('hostname_text', Input("hostname")),
        ('port_text', Input("port")),
    ])

 
provider_name = "foo"

@pytest.fixture
def webDriver(request):
    ensure_browser_open()
    login_admin()
 
    def closeSession():
        """ Close Browser """
    request.addfinalizer(closeSession)

    return 

""" Comment to test GPG """

""" Test Case """

def test_crud():
    sel.force_navigate('middleware_providers')
    time.sleep(3)
    sel.force_navigate("middleware_provider_new")
    time.sleep(1)
    fill(properties_form.name_text, provider_name)
    time.sleep(1)
    fill(properties_form, {"type_select": "Hawkular"})
    sel.wait_for_ajax()
    time.sleep(2)
    fill(properties_form.hostname_text, "127.0.0.1")
    time.sleep(2)
    add_button()
    flash.assert_success_message('Middleware Providers "{}" was saved'.format(provider_name))
    time.sleep(2)
    row = providers_table.find_row_by_cells({'name': provider_name})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    time.sleep(1)
    cfg_btn('Edit Selected Middleware Provider')
    time.sleep(1)
    fill(properties_form.port_text, "2020")
    time.sleep(2)
    save_button()
    time.sleep(2)
    flash.assert_success_message('Middleware Manager "{}" was saved'.format(provider_name))    
    sel.force_navigate('middleware_providers')
    time.sleep(2)
    row = providers_table.find_row_by_cells({'name': provider_name})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    time.sleep(1)
    cfg_btn('Remove Middleware Providers from the VMDB', invokes_alert=True)
    time.sleep(1)
    sel.handle_alert()
    time.sleep(1)
    flash.assert_success_message('Delete initiated for 1 Middleware Provider from the CFME Database')
    time.sleep(2)
    
    
    
    
    