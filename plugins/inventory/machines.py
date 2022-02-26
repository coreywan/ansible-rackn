from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from ansible.template import Templar

DOCUMENTATION = r'''
    name: rackn.drp.machines
    plugin_type: inventory
    author:
      - Corey Wanless (@coreywan)
    short_description: RackN DRP Machines Inventory Plugin
    version_added: "0.0.1"
    description:
        - This plugin allows you to query the RackN for machines and
          use the response data to populate the inventory file.
    extends_documentation_fragment:
      - inventory_cache
      - constructed
    options:
        rs_endpoint:
            description:
              - https path to the DRP Endpoint. Example 'https://10.10.10.6:8092'
            type: string
            required: True
            env:
                - name: RS_ENDPOINT
        rs_key:
            description:
              - Username:password to authenticate to DRP
            type: string
            required: True
            env:
                - name: RS_KEY
                - name: TOWER_PASSWORD
        validate_certs:
            description:
              - Validates certs or not
            default: False
            type: bool
        strict:
            description:
              - Accepts a key/value pair and uses it to filter the
                host records to be returned.
            default: False
            type: bool
        keyed_groups:
            description:
            - Add machines to group based on the values of a variable.
            type: list
            default: []
    requirements:
        - python >= 3.4
        - requests
'''

class InventoryModule(BaseInventoryPlugin, Constructable):

    NAME = 'rackn.drp.machines'  # used internally by Ansible, it should match the file name but not required

    def verify_file(self, path):
        ''' return true/false if this is possibly a valid file for this plugin to consume '''
        valid = True
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists and is readable by current user
            if path.endswith(('rackn.yml','rackn.yaml','drp.yml','drp.yaml')):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        
        # Basic Stuff
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self.loader = loader
        self.inventory = inventory
        self.templar = Templar(loader=loader)
        self._read_config_data(path)

        self.strict = self.get_option('strict')
        self.compose = self.get_option('compose')
        self.groups = self.get_option('groups')
        self.keyed_groups = self.get_option('keyed_groups')

        # Set some RACKN Variables
        self.rackn_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.rackn_user = self.get_option('rs_key').split(':')[0]
        self.rackn_pass = self.get_option('rs_key').split(':')[1]
        self.rackn_url = '{}/api/v3'.format(self.get_option('rs_endpoint'))
        self.rackn_validate_certs = self.get_option('validate_certs')

        # Let's go get some machine data
        get_machines_url = '{}/machines'.format(self.rackn_url)
        self.requests_auth = (self.rackn_user, self.rackn_pass)
        r = requests.get(get_machines_url,
            auth=self.requests_auth,
            headers=self.rackn_headers,
            verify=self.rackn_validate_certs)
        machine_info = r.json()

        # Let's process the machine data
        for machine in machine_info:
            self.inventory.add_host(machine['Name'])
            # loop through all the attributes of
            #   the rackn machine information and
            #   make it a variable on the machine with a prefix of rackn_
            for machine_key in machine:
                # Add initial Variables
                self.inventory.set_variable(machine['Name'],
                    'rackn_{}'.format(machine_key),
                    machine[machine_key])

            # Add variables created by the user's Jinja2 expressions to the host
            self._set_composite_vars(self.compose, machine, machine['Name'], strict=True)

            # The following two methods combine the provided variables dictionary with the latest host variables
            # Using these methods after _set_composite_vars() allows groups to be created with the composed variables
            self._add_host_to_composed_groups(self.groups, machine, machine['Name'], strict=self.strict)
            self._add_host_to_keyed_groups(self.keyed_groups, machine, machine['Name'], strict=self.strict)