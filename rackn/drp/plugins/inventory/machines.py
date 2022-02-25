from ansible.plugins.inventory import BaseInventoryPlugin
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

class InventoryModule(BaseInventoryPlugin):

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

        # Basic Stuff
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self.loader = loader
        self.inventory = inventory
        self.config = self._read_config_data(path)

        # Set some RACKN Variables
        self.rackn_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.rackn_user = self.config['rs_key'].split(':')[0]
        self.rackn_pass = self.config['rs_key'].split(':')[1]
        self.rackn_url = '{}/api/v3'.format(self.config['rs_endpoint'])
        self.rackn_validate_certs = self.config['validate_certs']

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
                self.inventory.set_variable(machine['Name'],
                    'rackn_{}'.format(machine_key),
                    machine[machine_key])
