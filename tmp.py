
def remove_twin_app_sids(sids, sids_to_stay,
                         notify_twin_clients=False,
                         notify_twin_services=False):
    """
        Remove socket_ids of twin applications from sids array;
        If sids_to_stay contain the twin app socket_id, then leave
        it in resulting array and remove the twin sid.
    """
    res = []
    # don't send notifications to twins of source sids (sids_to_stay)
    for s in sids_to_stay:
        if s in sids:
            res.append(s)
            if (sid_to_app[s]['type'] == 'client' and notify_twin_clients) or \
               (sid_to_app[s]['type'] == 'service' and notify_twin_services) :
                sids.remove(s)
            else:
                remove_sid_with_twins(sids, s)
    # override twin notification rules due to corresponding flags
    while sids:
        s = sids[0]
        res.append(s)
        if (sid_to_app[s]['type'] == 'client' and notify_twin_clients) or \
            (sid_to_app[s]['type'] == 'service' and notify_twin_services) :
            sids.pop(0)
        else:
            remove_sid_with_twins(sids, s)
    return res


def remove_sid_with_twins(sids, sid_to_remove):
    twin_sids_to_remove = app_name_to_sids[sid_to_app[sid_to_remove]['name']]
    for s in twin_sids_to_remove:
        sids.remove(s)

app_name_to_sids = {'MainUi': ['U5q4jvpEcUpN1mEXAAAN', '5mGy14kLDi_-auwTAAAR'],
                    'FileServiceNamespace': ['ni0KNaoWynPASzc1AAAJ'], }

sid_to_app = {'ni0KNaoWynPASzc1AAAJ': {'name': 'FileServiceNamespace', 'type': 'service'}, 
              'U5q4jvpEcUpN1mEXAAAN': {'name': 'MainUi', 'type': 'client'}, 
              '5mGy14kLDi_-auwTAAAR': {'name': 'MainUi', 'type': 'client'}}

subscription_sids = ['U5q4jvpEcUpN1mEXAAAN', '5mGy14kLDi_-auwTAAAR']

src_sids = ['U5q4jvpEcUpN1mEXAAAN', 'ni0KNaoWynPASzc1AAAJ']

res = remove_twin_app_sids(sids=subscription_sids,
                        sids_to_stay=src_sids,
                        notify_twin_clients=True,
                        notify_twin_services=True)

print(res)