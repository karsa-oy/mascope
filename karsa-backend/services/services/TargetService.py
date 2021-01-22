"""TOF Service
"""

import asyncio
import configparser
import io
import numpy as np
import pandas as pd
import socketio

from karsatof import kchem

from karsalib import BaseClientNamespace, BaseServiceClient, parse_cmd_args

from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File


class TargetServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for
        connecting to Router """

    rooms = ['target_list_request',
             ]

    service_state = dict(
        )

    async def on_target_list_request(self, data):
        global target_df
        cookies = data['cookies']
        target_df = read_remote_target_list()
        targets = get_target_table(target_df)
        targets.update({'cookies': cookies})
        await self.emit_client_notification('targets',
                                            targets
                                            )


def read_remote_target_list():
    config = configparser.ConfigParser()
    config.read_file( open('default.ini') )
    url = config['Sharepoint']['url']
    relative_url = config['Sharepoint']['relative_url']
    username = config['Sharepoint']['user']
    password = config['Sharepoint']['password']

    ctx_auth = AuthenticationContext(url)
    if ctx_auth.acquire_token_for_user(username, password):
        ctx = ClientContext(url, ctx_auth)
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()
        print("Web title: {0}".format(web.properties['Title']))
    else:
        print(ctx_auth.get_last_error())

    response = File.open_binary(ctx, relative_url)

    # save data to BytesIO stream
    bytes_file_obj = io.BytesIO()
    bytes_file_obj.write(response.content)
    bytes_file_obj.seek(0) #set file object to start

    # read file into pandas dataframe
    df = pd.read_excel(bytes_file_obj,
                       sheet_name=0,
                       engine='openpyxl'
                       )
    return df

def get_target_table(target_df, cols=None):
    if cols is None:
        cols = target_df.columns
    sub_df = target_df[cols]
    # Replace NaNs with Nones for JSON compatibility
    sub_df = sub_df.replace({np.nan: None})
    # Calculate ion m/z
    sub_df['Measured Ion m/z'] = [ kchem.get_exact_mass(comp) for comp in sub_df['Ion composition'] ]
    target_table = {'rows': list( sub_df.to_dict('index').values() ),
                    'cols': [ {'field': col,
                               'label': col.capitalize(),
                               }
                               for col in sub_df.columns ]
                    }
    return target_table


class TargetServiceClient(BaseServiceClient):
    pass

def run():
    client = TargetServiceClient(*parse_cmd_args(), TargetServiceNamespace)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())

if __name__=='__main__':
    run()