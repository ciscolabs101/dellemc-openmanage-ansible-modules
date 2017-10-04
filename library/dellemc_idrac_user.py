#! /usr/bin/python
# _*_ coding: utf-8 _*_

#
# Copyright (c) 2017 Dell Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: dellemc_idrac_user
short_description: Configures an iDRAC local User
version_added: "2.3"
description:
    - Configures an iDRAC local user
options:
  idrac_ip:
    required: False
    description: iDRAC IP Address
    default: None
  idrac_user:
    required: False
    description: iDRAC user name
    default: None
  idrac_pwd:
    required: False
    description: iDRAC user password
    default: None
  idrac_port:
    required: False
    description: iDRAC port
    default: None
  share_name:
    required: True
    description: CIFS or NFS Network share
  share_user:
    required: True
    description: Network share user in the format user@domain
  share_pwd:
    required: True
    description: Network share user password
  share_mnt:
    required: True
    description:
      - Local mount path of the network file share with read-write permission for ansible user
  user_name:
    required: True
    description: User name to be configured
  user_pwd:
    required: False
    description: User password
    default: None
  user_priv:
    required: False
    description: User privileges
    choices: ['Administrator', 'Operator', 'ReadOnly', 'NoAccess']
    default: 'NoPrivilege'
  state:
    description:
      - if C(present), will create/add/modify an user
      - if C(absent), will delete the user
      - if C(enable), will enable the user
      - if C(disable), will disable the user
    choices: ['present', 'absent', 'enable','disable']
    default: 'present'

requirements: ['omsdk']
author: anupam.aloke@dell.com
'''

EXAMPLES = '''
---
- name: Add a new iDRAC User
    dellemc_idrac_user:
      idrac_ip:   "192.168.1.1"
      idrac_user: "root"
      idrac_pwd:  "calvin"
      share_name: "\\\\192.168.10.10\\share"
      share_user: "user1"
      share_pwd:  "password"
      share_mnt:  "/mnt/share"
      user_name:  "newuser"
      user_pwd:   "password"
      user_priv:  "Administrator"
      state:      "present"

- name: Change password for the "newuser"
    dellemc_idrac_user:
      idrac_ip:   "192.168.1.1"
      idrac_user: "root"
      idrac_pwd:  "calvin"
      share_name: "\\\\192.168.10.10\\share"
      share_user: "user1"
      share_pwd:  "password"
      share_mnt:  "/mnt/share"
      user_name:  "newuser"
      user_pwd:   "newpassword"
      state:      "present"

- name: Change privilege for the "newuser"
    dellemc_idrac_user:
      idrac_ip:   "192.168.1.1"
      idrac_user: "root"
      idrac_pwd:  "calvin"
      share_name: "\\\\192.168.10.10\\share"
      share_user: "user1"
      share_pwd:  "password"
      share_mnt:  "/mnt/share"
      user_name:  "newuser"
      user_priv:  "Operator"
      state:      "present"

- name: Delete "newuser"
    dellemc_idrac_user:
      idrac_ip:   "192.168.1.1"
      idrac_user: "root"
      idrac_pwd:  "calvin"
      share_name: "\\\\192.168.10.10\\share"
      share_user: "user1"
      share_pwd:  "password"
      share_mnt:  "/mnt/share"
      user_name:  "newuser"
      state:      "absent"
'''

RETURN = '''
---
'''

from ansible.module_utils.dellemc_idrac import *
from ansible.module_utils.basic import AnsibleModule

try:
    from omdrivers.enums.iDRAC.iDRAC import Enable_UsersTypes, Privilege_UsersTypes
    HAS_OMSDK = True
except ImportError:
    HAS_OMSDK = False

def _setup_idrac_nw_share (idrac, module):
    """
    Setup local mount point for network file share

    idrac -- iDRAC handle
    module -- Ansible module
    """

    myshare = FileOnShare(module.params['share_name'],
                          module.params['share_mnt'],
                          isFolder=True)

    myshare.addcreds(UserCredentials(module.params['share_user'],
                                     module.params['share_pwd']))

    return idrac.config_mgr.set_liason_share(myshare)

def setup_idrac_user (idrac, module):
    """
    Setup iDRAC local user

    idrac  -- iDRAC handle
    module -- Ansible module
    """

    if not HAS_OMSDK:
        module.fail_json(msg="OpenManage Python SDK is required for this module")

    msg = {}
    msg['changed'] = False
    msg['failed'] = False
    msg['msg'] = {}
    err = False

    user_name = module.params['user_name']
    user_pwd = module.params['user_pwd']
    user_priv = None

    if module.params['user_priv']:
        if module.params['user_priv'] == "Administrator":
            user_priv = Privilege_UsersTypes.Administrator
        elif module.params['user_priv'] == "Operator":
            user_priv = Privilege_UsersTypes.Operator
        elif module.params['user_priv'] == "ReadOnly":
            user_priv = Privilege_UsersTypes.ReadOnly

    try:
        # Check first whether local mount point for network share is setup
        if idrac.config_mgr.liason_share is None:
            if not  _setup_idrac_nw_share (idrac, module):
                msg['msg'] = "Failed to setup local mount point for network share"
                msg['failed'] = True
                return msg

        # Check if user exists
        user = None

        if user_name:
            user = idrac.config_mgr._sysconfig.iDRAC.Users.find_first(UserName_Users=user_name)

        else:
            msg['msg'] = "Invalid user name provided"
            msg['failed'] = True
            return msg

        if module.params["state"] == "present":
            if not user:
                # Set the iDRAC user privilege to NoAccess if not provided
                if user_priv is None:
                    user_priv = Privilege_UsersTypes.NoAccess

                idrac.user_mgr.Users.new(
                                   UserName_Users = user_name.lower(),
                                   Password_Users = user_pwd,
                                   Privilege_Users = user_priv,
                                   Enable_Users = Enable_UsersTypes.Enabled)
            else:
                if user.Enable_Users.get_value() != Enable_UsersTypes.Enabled:
                    user.Enable_Users.set_value(Enable_UsersTypes.Enabled)

                if user_priv:
                    user.Privilege_Users.set_value(user_priv)

                if user_pwd is not None:
                    user.Password_Users.set_value(user_pwd)

        elif module.params["state"] == "enable":
            if user:
                user.Enable_Users.set_value(Enable_UsersTypes.Enabled)
            else:
                msg['msg'] = "User: " + user_name + " does not exist"
                msg['failed'] = True
                return msg

        elif module.params["state"] == "disable":
            if user:
                user.Enable_Users.set_value(Enable_UsersTypes.Disabled)
            else:
                msg['msg'] = "User: " + user_name + " does not exist"
                msg['failed'] = True
                return msg

        elif module.params["state"] == "absent":
            if user:
                idrac.config_mgr._sysconfig.iDRAC.Users.remove(UserName_Users = user_name)
            else:
                msg['msg'] = "User: " + user_name + " does not exist"
                msg['failed'] = True
                return msg

        msg['changed'] = idrac.config_mgr._sysconfig.is_changed()

        if module.check_mode:
            # Since it is running in check mode, reject the changes
            idrac.config_mgr._sysconfig.reject()
        else:
            msg['msg'] = idrac.config_mgr.apply_changes()

            if "Status" in msg['msg'] and msg['msg']['Status'] != "Success":
                msg['failed'] = True
                msg['changed'] = False

    except Exception as e:
        err = False
        msg['msg'] = "Error: %s" % str(e)
        msg['failed'] = True

    return msg, err

# Main
def main():

    module = AnsibleModule (
            argument_spec = dict (
                # iDRAC handle
                idrac      = dict (required = False, type='dict'),

                # iDRAC credentials
                idrac_ip   = dict (required = True, default = None, type='str'),
                idrac_user = dict (required = True, default = None, type='str'),
                idrac_pwd  = dict (required = True, default = None, type='str', no_log = True),
                idrac_port = dict (required = False, default = None, type = 'int'),

                # Network File Share
                share_name = dict (required = True, type = 'str'),
                share_user = dict (required = True, type = 'str'),
                share_pwd  = dict (required = True, type = 'str'),
                share_mnt  = dict (required = True, type = 'path'),

                # Local user credentials
                user_name  = dict (required = True, type='str'),
                user_pwd   = dict (required = False, default = None, type='str', no_log = True),
                user_priv  = dict (required = False,
                                   choices = ['Administrator', 'Operator', 'ReadOnly', 'NoAccess'],
                                   default = None),

                # State
                state = dict (required = False,
                              choices = ['present', 'absent', 'enable', 'disable'],
                              default = 'present')
                ),

            supports_check_mode = True)

    # Connect to iDRAC
    idrac_conn = iDRACConnection (module)
    idrac = idrac_conn.connect()

    # Setup User
    msg, err = setup_idrac_user (idrac, module)

    # Disconnect from iDRAC
    idrac_conn.disconnect()

    if err:
        module.fail_json(**msg)
    module.exit_json(**msg)


if __name__ == '__main__':
    main()
