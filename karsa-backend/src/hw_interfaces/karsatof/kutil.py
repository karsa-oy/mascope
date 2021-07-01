# -*- coding: utf-8 -*-
"""
Created on Wed Apr 03 09:19:39 2019

@author: Oskari Kausiala
"""

import numpy as np
import pandas as pd

import h5py
import h5sparse
import sqlite3
import random
import string

from datetime import datetime, timedelta
from collections import namedtuple
from multiprocessing import Queue
from queue import Empty

from .kchem import get_exact_mass, get_exact_isotope_masses


def filetime2datetime(timestamp):
    """Function to convert timestamp in FILETIME format to datetime

    Parameters
    ----------
    timestamp : int64
        Number of 100-nanosecond intervals since January 1, 1601

    Returns
    -------
    datetime
        Input timestamp converted to datetime format
    """

    _FILETIME_null_date = datetime(1601, 1, 1, 0, 0, 0)
    return _FILETIME_null_date + timedelta(microseconds=timestamp / 10)


def write_sampleid(filename, sampleid):
    """Write Sample ID to h5 file

    Writes the Sample ID to group /Karsa as an attribute. If the group
    does not exist, it will be created.

    Parameters
    ----------
    filename : str
        Full file path
    sampleid : str
        Sample ID
    """

    with h5py.File(filename, 'r+') as h5f:
        if 'Karsa' not in h5f:
            h5f.create_group('Karsa')
        h5f['Karsa'].attrs['Sample ID'] = sampleid


def read_sampleid(filename):
    """Read Sample ID from a h5 file

    Tries to read the Sample ID from group /Karsa attributes.
    Returns None if the Sample ID could not be read.

    Parameters
    ----------
    filename : str
        Full file path

    Returns
    -------
    str
        Sample ID
    """

    try:
        with h5py.File(filename, 'r') as h5f:
            sampleid = h5f['Karsa'].attrs['Sample ID']
            return sampleid
    except BaseException:
        return None
    
def write_description(filename, description):
    """Write Sample Description to h5 file

    Writes the Sample Description to group /Karsa as an attribute.
    If the group does not exist, it will be created.

    Parameters
    ----------
    filename : str
        Full file path
    description : str
        Sample description
    """

    with h5py.File(filename, 'r+') as h5f:
        if 'Karsa' not in h5f:
            h5f.create_group('Karsa')
        h5f['Karsa'].attrs['Sample description'] = description


def read_description(filename):
    """Read Sample description from a h5 file

    Tries to read the Sample description from group /Karsa attributes.
    Returns None if the Sample description could not be read.

    Parameters
    ----------
    filename : str
        Full file path

    Returns
    -------
    str
        Sample description
    """

    try:
        with h5py.File(filename, 'r') as h5f:
            description = h5f['Karsa'].attrs['Sample description']
            return description
    except BaseException:
        return None


def write_peak_dict(D, filename):
    """Write peak dictionary (sparse matrix) to h5 file.

    Parameters
    ----------
    D : csr
        Peak dictionary (sparse matrix)
    filename : str
        Full file path
    """

    # Write peak dictionary D in Scipy sparse CSR format into a h5 file
    with h5sparse.File(filename, 'w') as h5f:
        h5f.create_dataset('sparse/matrix', data=D)
    return


def load_peak_dict(filename):
    """Load peak dictionary (sparse matrix) from h5 file.

    Parameters
    ----------
    filename : str
        Full file path

    Returns
    -------
    csr
        Peak dictionary (sparse matrix)
    """

    # Load peak dinctionary D in Scipy sparse CSR format from a h5 file
    with h5sparse.File(filename, 'r') as h5f:
        D = h5f['sparse/matrix'].value
    return D


def get_peaklist_all_tables_rows(peaklist_path, tables):
    """Read peaklist SQLite database

    NOTE: !!! Not sure how this is supposed to be used !!!

    Parameters
    ----------
    peaklist_path : str
        Full file path
    tables : list
        db tables to fetch

    Returns
    -------
    dict
        Database contents
    """

    try:
        conn = sqlite3.connect(peaklist_path)
    except:
        return {}
    c = conn.cursor()
    all_rows = {}

    for table in tables:
        columns = c.execute("SELECT * FROM {}".format(table)).description
        all_rows[table] = []

        for row in c.fetchall():
            dict_ = {}
            for (index, value) in enumerate(row):
                dict_[columns[index][0]] = value
            all_rows[table].append(dict_)

    conn.close()
    return all_rows


def update_peaklist_db_peaks_table(peaklist_path, table, task, values):
    """Add data to peaklist SQLite database

    NOTE: !!! Not sure how this is supposed to be used !!!

    Parameters
    ----------
    peaklist_path : str
        Full file path
    table : str
        Table to modify, only used if 'task' is either 'edit' or 'delete'.
    task : str
        Task to perform to selected table, allowed values:
        'create', 'edit' or 'delete'
    values : dict
        Not sure what this should be ???

    Returns
    -------
    None
    """

    if peaklist_path is None or table is None or task is None or values is None:
        return
    else:
        try:
            conn = sqlite3.connect(peaklist_path)
        except:
            return

        c = conn.cursor()
        query = ""

        if task == "create":
            columns = '`, `'.join(list(values.get("db_row_pairs").keys()))
            query_values = "', '".join(
                list(values.get("db_row_pairs").values()))
            molComp = values.get("db_row_pairs").get("molComp")
            mass = get_exact_mass(molComp)[0]
            query = """ INSERT INTO {} (`pId`, `mass`, `{}`) 
                        VALUES ((SELECT MAX(pId) FROM peaks) + 1, {},  '{}') """.format(
                        'peaks', columns, str(mass), query_values)
            c.execute(query)
            last_inserted_id = c.lastrowid
            conn.commit()

            # isotope table needs inserted values generated by get_exact_isotope_masses
            isotope_values = get_exact_isotope_masses(molComp)
            try:
                for i in range(0, len(isotope_values[0])):
                    q = """INSERT INTO isotopes (`pId`, `mass`, `abundance`) VALUES ({}, {}, {})""".format(
                        last_inserted_id, str(isotope_values[0][i]),
                        str(isotope_values[1][i]))
                    c.execute(q)
                    conn.commit()
            except:
                # rollback if first qury succedded but second query failed..
                if last_inserted_id is not None:
                    c.execute(
                        """ DELETE FROM isotopes WHERE pId = (
                        SELECT MAX(pId) FROM peaks) """
                    )
                    conn.commit()
        else:
            primary_column_id = values.get("primary_column_id")
            primary_column_value = "{}{}{}".format(
                    "'", 
                    values.get("primary_column_value"),
                    "'"
                ) if values.get("primary_column_value"
                    ) is not None else (
                        'NULL OR {}=""'.format(primary_column_id)
                    )
            operator = "=" if values.get(
                "primary_column_value") is not None else " is "

        if task == "edit":
            set_query_part = (",").join([
                key + "='" + str(value) + "'"
                for key, value in values.get("db_row_pairs").items()
            ])
            query = "UPDATE {} SET {} WHERE {} {} {}".format(
                table, set_query_part, primary_column_id, operator,
                primary_column_value)
            c.execute(query)
            conn.commit()

        if task == "delete":
            query = "DELETE FROM {} WHERE {} {} {}".format(
                table, primary_column_id, operator, primary_column_value)
            c.execute(query)
            conn.commit()

            # now cleanup the table where pId is not equal to pId In Isotopes, 
            # also removes invalid rows in isotope table
            query = """DELETE FROM isotopes 
                        WHERE isotopes.pId not IN ( SELECT DISTINCT(pId) FROM peaks) """
            c.execute(query)
            conn.commit()

        conn.close()


def read_peaklist(filename, min_iso_abu=0.4):
    """Read peaklist SQLite database, generated in tofTools

    Parameters
    ----------
    filename : str
        Full file path
    min_iso_abu : float, optional
        For each compound in the db, all isotopes with relative abundance
        greater than this will be returned, by default 0.4

    Returns
    -------
    dict
        Dictionary with contents of the peaklist db
    """

    # Set up a named tuple
    Peak = namedtuple('Peak', 'pId, ref, molComp')
    # Read database file
    try:
        conn = sqlite3.connect(filename)
    except:
        return {}
    c = conn.cursor()
    c.execute("SELECT pId, reference, molComp FROM peaks")
    # Peaks
    peaks = []
    for pk in map(Peak._make, c.fetchall()):
        peaks.append(pk)
    # Isotopes
    c.execute("SELECT pId, mass, abundance FROM isotopes")
    isotopes = c.fetchall()
    # Make peak dict
    peaklist = {}
    for peak in peaks:
        if peak[0] not in peaklist:
            peaklist[peak[0]] = {}
        peaklist[peak[0]]['molComp'] = peak[2]
        peaklist[peak[0]]['ref'] = peak[1]
    # Make isotope dict
    isotopelist = {}
    for iso in isotopes:
        if iso[2] < min_iso_abu:
            continue
        if iso[0] not in isotopelist:
            isotopelist[iso[0]] = {}
            isotopelist[iso[0]]['abundance'] = []
            isotopelist[iso[0]]['mass'] = []
        isotopelist[iso[0]]['abundance'].append(iso[2])
        isotopelist[iso[0]]['mass'].append(iso[1])
    # Merge peaks and isotopes
    pl = {}
    for pId, vals in peaklist.items():
        if pId in isotopelist.keys():
            if len(vals['ref']) > 0:
                key = vals['ref']
            else:
                key = peaklist[pId]['molComp']
            pl[key] = isotopelist[pId]
            pl[key]['molComp'] = peaklist[pId]['molComp']
    try:
        # Identification parameters
        c.execute("SELECT reference, threshold, mzErrTol, \
                  isoAbuTol, isoPearR FROM idparams")
        id_params = c.fetchall()
        # Add id parameters to peaklsit dict
        for par in id_params:
            if par[0] in pl.keys():
                pl[par[0]]['idPar'] = (par[1], par[2], par[3], par[4])
    except:
        for pId in pl.keys():
            pl[pId]['idPar'] = (0, 0, 0, 0)
    conn.close()
    return pl


def peaklist_to_df(peaklist):
    """Convert peaklist dictionary to a DataFrame

    Parameters
    ----------
    peaklist : dict
        Peaklist dictionary as returned by the function 'read_peaklist'

    Returns
    -------
    DataFrame
        Peaklist as a DataFrame
    """

    df = pd.DataFrame()
    df['molComp'] = []
    df['mass'] = []
    df['mass'] = df['mass'].astype(object)
    df['abundance'] = []
    df['abundance'] = df['abundance'].astype(object)

    keys = peaklist.keys()
    molComps = [vals['molComp'] for pId, vals in peaklist.items()]
    masses = [np.array(vals['mass']) for pId, vals in peaklist.items()]
    abus = [np.array(vals['abundance']) for pId, vals in peaklist.items()]
    idpar = [np.array(vals['idPar']) for pId, vals in peaklist.items()]

    df['molComp'] = molComps
    df['mass'] = masses
    df['abundance'] = abus
    df['idPar'] = idpar
    df.index = keys
    return df


def write_detection_par_to_pl(filename, peak_df):
    """Write detection parameters to peaklist SQLite database

    Parameters
    ----------
    filename : str
        Full file path
    peak_df : DataFrame
        Peaklist DataFrame (with the detection parameters)

    Raises
    ------
    Warning
        Warning is raised if database could not be modified
    """

    try:
        conn = sqlite3.connect(filename)
    except:
        raise Warning('Writing to peaklist \
                      database %s failed!' % filename)
    c = conn.cursor()
    # Check if idparams table exists
    #get the count of tables with the name
    c.execute(''' SELECT count(name) FROM sqlite_master 
              WHERE type='table' AND name='idparams' ''')
    if c.fetchone()[0] != 1:
        # Does not exist, create table
        c.execute('''CREATE TABLE idparams
          (reference text, mzErrTol real, \
          isoAbuTol real, isoPearR real)''')

    for pref, p in peak_df.iterrows():
        c.execute(
            '''UPDATE idparams
                  SET threshold = ?,
                      mzErrTol = ?,
                      isoAbuTol = ?,
                      isoPearR = ?
                  WHERE reference = ?''',
            (p['idPar'][0], p['idPar'][1], p['idPar'][2], p['idPar'][3], pref))
    # Save (commit) the changes
    conn.commit()
    conn.close()


def ct_struct_to_dict(struct):
    """Convert ctypes struct to dict

    Parameters
    ----------
    struct : Structure
        ctypes Structure to convert

    Returns
    -------
    dict
        Dictionary with the 'struct' contents
    """

    result = {}
    for field, _ in struct._fields_:
         value = getattr(struct, field)
         # if the type is not a primitive and it evaluates to False ...
         if (type(value) not in [int, float, bool]) and not bool(value):
             # it's a null pointer
             value = None
         elif hasattr(value, "_length_") and hasattr(value, "_type_"):
             # Probably an array
             value = list(value)
         elif hasattr(value, "_fields_"):
             # Probably another struct
             value = ct_struct_to_dict(value)
         elif type(value) == bytes:
             value = value.decode()
         result[field] = value
    return result



def generate_unique_key():
    """Generate a 15 character long random string

    Returns
    -------
    str
        Random string with 15 characters
    """

    CHARACTERS = (
    string.ascii_letters
    + string.digits
    + '-._~'
    )
    return ''.join(random.sample(CHARACTERS, 15))


class AttrDict(dict):
    """Dict object that allows accessing values like attributes
    (dot notation).

    Example:
    d = AttrDict({'a': 0})  # initialize AttrDict with a dict
    d.a                     # returns 0
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize self
        """
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
                

class SubscriptableQueue(object):
    """Subscriptable Queue object
    
    Threads or Processes can subscribe to this object with
    a unique identifier, allowing synchronization between
    producer and consumer threads. It is intended to be used
    within the producer thread in place of a standard Queue, in
    cases where multiple consumers need to have simultaneous access 
    to the queue. Use instances of 'QueueSubscription' in place 
    of a standard Queue within the consumer threads to allow direct
    replacement of a Queue object.

    Attributes
    ----------
    queues : dict
        Dictionary holding the subscriptions to this instance,
        keys are unique identifiers for each subscriber and the
        values are their corresponding (standard) Queue objects.
    """

    def __init__(self):
        """Initialize self
        """

        self.queues = {}

    def __bool__(self):
        """
        Returns
        -------
        bool
            Returns True if there are any subscribers, False otherwise
        """
        return len(self.queues) > 0

    def put(self, val):
        """Put value to the queue of each subscriber

        Only the producer thread should call the put method, to avoid
        incompatibilities (i.e. to keep consumers independent of each other).

        Parameters
        ----------
        val : any
            Data to put
        """

        for ident, q in self.queues.items():
            q.put(val)

    def get(self, ident, *args, **kwargs):
        """Get from the queue with key 'ident'. Extra arguments will
        be passed to the queue.get() method.

        Parameters
        ----------
        ident : str
            Key of the subscriber

        Returns
        -------
        any
            Return the next object in the queue
        """

        return self.queues.get(ident).get(*args, **kwargs)

    def get_nowait(self, ident, *args, **kwargs):
        """Get without blocking from the queue with key 'ident'.
        Extra arguments will be passed to the queue.get_nowait() method.

        Parameters
        ----------
        ident : str
            Key of the subscriber

        Returns
        -------
        any
            Return the next object in the queue (if any)
        """
        
        return self.queues.get(ident).get_nowait(*args, **kwargs)

    def qsize(self, ident, *args, **kwargs):
        """Get size of the queue with key 'ident'

        Parameters
        ----------
        ident : str
            Key of the subscriber

        Returns
        -------
        int
            Queue size
        """

        return self.queues.get(ident).qsize(*args, **kwargs)

    def subscribe(self, ident):
        """Subscribe to this instance

        Parameters
        ----------
        ident : str
            Key to subscribe with, must be unique

        Raises
        ------
        Exception
            Exception is raised if a subscriber with the same key exists
            already.
        """

        if ident in self.queues.keys():
            raise Exception('name %s already subscribed' %ident)
        else:
            self.queues.update({ident: Queue()})

    def close(self):
        """Close all queues
        """

        for ident, q in self.queues.items():
            q.close()
            
    def join_thread(self):
        """Join all queue threads
        """

        for ident, q in self.queues.items():
            q.close()
            
class QueueSubscription():
    """Object to use in place of a standard Queue within a consumer thread,
    when using SubscriptableQueue within the producer thread.

    Attributes
    ----------
    q : SubscriptableQueue
        Instance to subscribe to
    ident : str
        Unique identifier of this subscription
    """

    def __init__(self, subscriptable_q, ident=None):
        """Initialize self

        Subscribe to the 'subscriptable_q' with the key 'ident'.
        If 'ident' is not given, it will be automatically generated.

        Parameters
        ----------
        subscriptable_q : SubscriptableQueue
            Instance to subscribe to
        ident : str, optional
            Unique identifier of this subscription, by default None.
            If None, it will be automatically generated.
        """

        self.q = subscriptable_q
        # Subscribe to a subscriptable queue
        if ident is None:
            ident = generate_unique_key()
        self.ident = ident
        self.q.subscribe(ident)

    def get(self, *args, **kwargs):
        """Get from the queue

        Returns
        -------
        any
            Next object in the queue
        """

        # Get from the queue
        return self.q.get(self.ident, *args, **kwargs)

    def get_nowait(self, *args, **kwargs):
        """Get from the queue without waiting

        Returns
        -------
        any
            Next object in the queue (if not empty)

        Raises
        ------
        Exception
            Raises an exception if the queue is empty
        """

        try:
            return self.q.get_nowait(self.ident, *args, **kwargs)
        except Empty:
            raise Empty

    def qsize(self, *args, **kwargs):
        """Get queue size

        Returns
        -------
        int
            Number of objects in the queue
        """

        return self.q.qsize(self.ident, *args, **kwargs)