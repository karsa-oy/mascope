# -*- coding: utf-8 -*-
"""File Service

This script runs the file service for Karsa Tarkka TOF system.

FileService connects to the :mod:`~router_service.router_service.Router`
via socket.io, and handles file i/o synchronization.
      
Created on Thu May  7 12:43:13 2020
"""

import asyncio
import csv
import os
import tempfile
import dateutil.parser
import json

from karsalib.client import (
                        BaseClientNamespace,
                        BaseServiceClient
                        )
from karsalib.util import (
                        parse_cmd_args,
                        get_client_notification_context,
                        get_date_time_from_sample_name
                        )
from karsalib.db import SampleManagerDB
from karsalib.datapool import SampleCatalog
from karsaHT3000A.ht3000a import parse_csv_report, dup_cycles


projects_path = 'Projects' # TODO: make configurable
datapool = SampleCatalog(projects_path)

class MetadataServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    service_state = dict(
        projects = {'value': datapool.get_projects(), 'room': 'projects'},
    )

    # ========== UI requests ==========
    async def on_experiment_selected(self, data):
        value = data['value']
        self.log(value)
        kwargs = get_client_notification_context(data)
        experiment = value.get('title')
        project = value.get('project')

        global datapool
        # Update sample table data
        await self.emit_client_notification(
                            'samples',
                            datapool.get_samples(project, experiment).to_dict(orient='index'),
                            **{**kwargs,
                               'room': data['client_room']
                               },
                            )

    async def on_experiment_from_plan(self, data):
        global datapool

        value = data['value']
        experiment = value['title']
        attributes = value['attributes']
        project = value['project']
        template_raw_text = value['template_to_parse']
        # TODO: Currently assumes autosampler report
        import tempfile
        fd, report_temp_path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(template_raw_text)
            sequence_steps = parse_csv_report(report_temp_path)
        finally:
            os.remove(report_temp_path)

        # Create experiment
        project_experiments = datapool.pool.get(project).keys()
        if experiment in project_experiments:
            raise ValueError("Experiment with given name already exists under project: %s" %project)
        sample_attributes_template = []
        for key in sequence_steps[0].keys():
            sample_attr = {
                'label': key,
                'value': "",
            }
            sample_attributes_template.append(sample_attr)
        datapool.new_experiment(project,
                                experiment,
                                attributes,
                                sample_attributes_template
                                )

        # Create placeholders for each sample
        for i, step in enumerate(sequence_steps):
            sample_attributes = []
            for key, value in step.items():
                sample_attr = {
                    'label': key,
                    'value': value,
                }
                sample_attributes.append(sample_attr)

            filename = '%03d_placeholder' %(i+1)
            datapool.new_sample(project,
                                experiment,
                                filename,
                                sample_attributes,
                                placeholder=True
                                )
        
    async def on_import_sample_table_datetime_range(self, data):
        global datapool
        kwargs = get_client_notification_context(data)
        # Update sample table data
        # await self.emit_client_notification(
        #                     'importable_samples',
        #                     datapool.get_samples().to_dict(orient='index'),
        #                     **{**kwargs,
        #                        'room': data['client_room']
        #                       }
        #                     )
        dt_min = dateutil.parser.isoparse(data['value']['dt0'])
        dt_max = dateutil.parser.isoparse(data['value']['dt1'])
        samples = self.parent.store.between('date',
                                            f"{dt_min.year}.{dt_min.month}.{dt_min.day}",
                                            f"{dt_max.year}.{dt_max.month}.{dt_max.day}")
        self.log(samples)
        if not samples:
            return
        cols = [{'field':k, 'label':k} for k in samples[0]]
        await self.emit_client_notification(
                            'importable_samples',
                            {'cols': cols, 'rows': samples},
                            **{**kwargs,
                               'room': data['client_room']
                              }
                            )

    async def on_parse_experiment_plan_blob(self, data):
        value = data['value']
        kwargs = get_client_notification_context(data)
        # Differentiate autosampler report from generic csv
        autosampler_report = value.startswith("HT3000A Autorun Report")
        # Make temp file for csv reader
        fd, report_temp_path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'r+') as tmp:
                tmp.write(value)
                tmp.seek(0)
                if autosampler_report:
                    sequence_steps = parse_csv_report(tmp)
                    sequence_steps = dup_cycles(sequence_steps)
                else:
                    sequence_steps = [row for row in csv.DictReader(tmp)]
        finally:
            os.remove(report_temp_path)
        # Parse sequence steps into template
        sample_attributes_template = []
        samples = []
        for i, step in enumerate(sequence_steps):
            sample = {'title': '%03d_' %(i+1)}
            sample_attributes = []
            for key, value in step.items():
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                sample_attr = {
                    'label': key,
                    'value': value,
                }
                sample_attributes.append(sample_attr)
                if i==0:
                    sample_attributes_template.append({'label': key,
                                                       'value': "",
                                                       })
            sample.update({'attributes': sample_attributes})
            samples.append(sample)

        experiment_plan = {
            'sample_attributes_template': sample_attributes_template,
            'sample_placeholders': samples,
            }
        await self.emit_client_notification('experiment_plan',
                                            experiment_plan,
                                            **{**kwargs,
                                                'room': data['client_room'],}
                                            )

    async def on_project_selected(self, data):
        global datapool
        value = data['value']
        kwargs = get_client_notification_context(data)
        project = value.get('title')

        if project not in datapool.pool.keys():
            raise ValueError("Requested project does not exist!")

        experiments = datapool.get_experiments(project)
        await self.emit_client_notification(
                                    'experiments',
                                    experiments,
                                    **{**kwargs,
                                       'room': data['client_room']
                                      },
                                )
    
    async def on_delete_experiment(self, data):
        global datapool
        self.log(data)
        value = data['value']
        experiment = value['experiment']
        project = value['project']
        kwargs = get_client_notification_context(data)
        datapool.delete_experiment(project, experiment)

        # == new sm db style =======
        self.parent.db.catalog_remove('/'.join(['', project, experiment]))
        project_experiments = self.parent.db.catalog.get(parent_id='/'.join(['', project]))
        # ==========================

        project_experiments = datapool.get_experiments(project)
        await self.emit_client_notification(
                        'experiments',
                        project_experiments,
                        **{**kwargs,
                            'room': project,},
                        )

    async def on_delete_project(self, data):
        global datapool
        self.log(data)
        value = data['value']
        project = value['project']
        kwargs = get_client_notification_context(data)
        datapool.delete_project(project)

        # == new sm db style =======
        self.parent.db.catalog_remove('/'.join(['', project]))
        projects = self.parent.db.catalog.get(parent_id='/')
        # ==========================

        projects = datapool.get_projects()
        await self.emit_client_notification(
                                    'projects',
                                    projects,
                                    **kwargs,
                                    )

    async def on_delete_sample(self, data):
        ''' Remove sample from an experiment '''
        global datapool
        value = data['value']
        filename = value['filename']
        experiment = value['experiment']
        project = value['project']
        kwargs = get_client_notification_context(data)
        try:
            datapool.delete_sample(project, experiment, filename)
        except Exception as e:
            self.log('Error:', str(e))
        # Update sample table data in UIs
        await self.emit_client_notification(
                            'samples',
                            datapool.get_samples(project, experiment).to_dict(orient='index'),
                            **{**kwargs,
                                'room': '_'.join([project, experiment])},
                            )

    async def on_save_experiment(self, data):
        value = data['value']
        self.log(value)
        experiment = value.get('title')
        project = value.get('project')
        attributes = value.get('attributes')
        sample_attributes_template = value.get('sample_attributes_template')
        sample_placeholders = value.get('sample_placeholders', [])
        kwargs = get_client_notification_context(data)
        # Create new experiment directory

        if project not in datapool.pool.keys():
            raise ValueError("Requested project does not exist!")
        project_experiments = datapool.pool.get(project).keys()
        if experiment not in project_experiments:
            # New experiment
            datapool.new_experiment(project,
                                    experiment,
                                    attributes,
                                    sample_attributes_template
                                    )
        else:
            # Edit existing experiment
            datapool.edit_experiment(project,
                                     experiment,
                                     attributes,
                                     )

        # == new sm db style; TODO: edit, parse input attrs =======
        self.parent.db.catalog_mkdir('/'.join(['', project, experiment]))
        project_experiments = self.parent.db.catalog.get(parent_id='/'.join(['', project]))
        # ==========================

        # Create placeholders for each sample
        for i, sample_placeholder in enumerate(sample_placeholders):
            filename = '%03d_placeholder' %(i+1)
            datapool.new_sample(project,
                                experiment,
                                filename,
                                sample_placeholder.get('attributes', []),
                                sample_placeholder.get('method', {}),
                                sample_placeholder.get('annotations', []),
                                placeholder=True
                                )

        project_experiments = datapool.get_experiments(project)
        await self.emit_client_notification(
                        'experiments',
                        project_experiments,
                        **{**kwargs,
                            'room': project,}
                        )

    async def on_save_project(self, data):
        value = data['value']
        self.log(value)
        project = value.get('title')
        attributes = value.get('attributes')
        kwargs = get_client_notification_context(data)
        if project not in datapool.pool.keys():
            # New project
            datapool.new_project(project, attributes)
        else:
            # Edit existing project
            datapool.edit_project(project, attributes)

        # == new sm db style; TODO: edit project, parse input attrs =======
        self.parent.db.catalog_mkdir('/'.join(['', project]))
        projects = self.parent.db.catalog.get(parent_id='/')
        # ==========================

        projects = datapool.get_projects()
        await self.emit_client_notification(
                                    'projects',
                                    projects,
                                    **kwargs,
                                    )


    async def on_save_sample(self, data):
        """Write attributes of a sample to disk. Make a symbolic link from
        the sample directory in 'data_path' to 'project_path'/experiment
        Parameters
        ----------
        data : [type]
            [description]

        Raises
        ------
        ValueError
            [description]
        """
        global datapool
        value = data['value']
        kwargs = get_client_notification_context(data)

        async def save_single_sample(sample_data):
            self.log(sample_data)
            filename = sample_data['filename']
            experiment = sample_data['experiment']
            project = sample_data['project']
            attributes = sample_data.get('attributes')
            method = sample_data.get('method')
            annotations = sample_data.get('annotations', [])
            # TODO: TMP ugly workaround: if sample comes from SampleManagerDB.store,
            # then mock up attrs, which should come from parent's db item.
            attributes = attributes or [
                {'label':'title', 'value': filename},
                {'label':'description', 'value': ''},
                {'label':'project', 'value': project},
                {'label':'experiment', 'value': experiment},
            ]
            try:
                samples = datapool.pool.get(project).get(experiment)
            except KeyError:
                raise ValueError("Requested project or experiment does not exist!")
            if filename not in samples:
                # New sample attributes
                datapool.new_sample(project, experiment, filename, attributes, method, annotations)
            else:
                # Edit sample attributes
                datapool.edit_sample(project, experiment, filename, attributes, method)


            # == new sm db style; TODO: edit, parse input attrs =======
            self.parent.db.catalog_add('/'.join(['', project, experiment, filename]), filename)
            experiment_samples = self.parent.db.catalog.get(parent_id='/'.join(['', project, experiment]))
            # ==========================


            # Update sample table data in UIs
            await self.emit_client_notification(
                                'samples',
                                datapool.get_samples(project, experiment).to_dict(orient='index'),
                                **{**kwargs,
                                    'room': '_'.join([project, experiment])}
                                )

        if isinstance(value, list):
            for sample_data in value:
                await save_single_sample(sample_data)
        else:
            await save_single_sample(value)


    async def on_save_sample_annotation(self, data):
        global datapool
        value = data['value']
        filename = value['filename']
        project = value['project']
        experiment = value['experiment']
        annotation = value['annotation']
        datapool.annotate_sample(project, experiment, filename, annotation)

    async def on_dataset_updated(self, data):
        value = data['value']
        if value['data_type'] != 'signal':
            raise ValueError(f"Expected data_type: signal - got {value['data_type']}")
        filename = value['filename']
        full_length = value['length']
        committed_length = value['committed_length']
        if committed_length >= full_length:
            # update sample store
            datetime, date, time = get_date_time_from_sample_name(filename)
            sample_store_data = {
                'filename': filename,
                'instrument': filename.split('_')[0],
                'date': date,
                'time': time,
                'length': committed_length,
            }
            self.parent.db.store_add(**sample_store_data)

    # ---------------------------------


class SampleManagerClient(BaseServiceClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = SampleManagerDB(':memory:')
        self.store = self.db.store
        self.catalog = self.db.catalog


def run():
    args = parse_cmd_args()
    client = SampleManagerClient(args['url'],
                                 args['port'],
                                 (args['ns'], MetadataServiceNamespace)
                                 )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt as e:
        print(f"{client.__class__.__name__} : {e.__class__.__name__}({str(e)})")
    except Exception as e:
        print(f"{client.__class__.__name__} : {e.__class__.__name__}({str(e)})")
    finally:
        client.shutdown_event.set()
        print(f'Service stopped.')



if __name__=='__main__':
    run()
