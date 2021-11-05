<template>
    <div>
    <!-- Modals -->
        <!-- Landing modal -->
        <section class="landing-modal">
            <b-modal :active.sync="is_modal_landing_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="false"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">
                                Select project and experiment
                            </p>
                        </header>
                        <section class="modal-card-body">
                            <b-field label="Project">
                                <b-select
                                    placeholder="Select a project"
                                    @input="selectProject($event)"
                                    required
                                    expanded>
                                    <option
                                        v-for="p in projects"
                                        :value="p.title"
                                        :key="p.title">
                                        {{ p.title }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-button
                                expanded
                                @click="launchProjectAttributesModal('new')">
                                New Project
                            </b-button>

                            <div><br></div>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    @input="selectExperiment($event)"
                                    :disabled="!project_selected.title"
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments"
                                        :value="e.title"
                                        :key="e.title">
                                        {{ e.title }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-button
                                expanded
                                @click="launchNewExperimentModal()"
                                :disabled="!project_selected.title">
                                New Experiment
                            </b-button>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                @click="is_modal_landing_active=false"
                                is-dark
                                :disabled="!(project_selected.title.length && experiment_selected.title.length)">
                                Proceed
                            </b-button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>     
        <!-- End of landing modal -->
        
        <!--- Project attributes modal--> 
        <section class="project-attribute-modal">
            <b-modal :active.sync="is_modal_project_attributes_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px">
                    <!-- Main content -->
                    <div class="columns">
                        <!-- Left side -->
                        <div class="column">
                            <header class="modal-card-head">
                                <p class="modal-card-title">
                                    {{project_form_props.title}}
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <MetaDataForm
                                    form_title="Project attributes"
                                    :default_template="project_form_props.default_template"
                                    :editable="project_form_props.editable"
                                    :initial_template="project_form_props.initial_template"
                                    :template_path="project_form_props.template_path"
                                    @metaDataUpdated="project_attributes_fields=$event">
                                </MetaDataForm>
                            </section>
                        </div>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button
                            :disabled="false"
                            @click="saveProject()">
                            Save
                        </b-button>
                        <b-button
                            @click="cancelNewProject()">
                            Cancel
                        </b-button>
                        <div
                            v-if="project_form_props.initial_template"
                            style="position:absolute; right:20px">
                            <b-tooltip
                                label="Delete project"
                                position="is-left"
                                :delay="1000">
                                <b-button
                                    type="is-danger"
                                    icon-left="delete"
                                    @click="deleteProject(project_form_props.initial_template[0].value)">
                                </b-button>
                            </b-tooltip>
                        </div>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of project attributes modal--> 

        <!--- New experiment modal--> 
        <section class="experiment-attribute-modal">
            <b-modal
                :active.sync="is_modal_new_experiment_active"
                has-modal-card
                trap-focus
                :can-cancel="true">
                <div class="modal-card" style="width: 500px">
                    <div class="columns">
                        <div class="column">
                            <header class="modal-card-head">
                                <p class="modal-card-title">
                                    New experiment
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <!-- Experiment attributes form -->
                                <MetaDataForm
                                    form_title="Experiment attributes"
                                    :default_template="experiment_attributes_default_template"
                                    :editable="true"
                                    :template_path="experiment_attributes_template_path"
                                    @metaDataUpdated="experiment_attributes_fields=$event">
                                </MetaDataForm>
                                <!-- End of experiment attributes form -->
                                <div><br></div>
                                <!-- Upload experiment plan -->
                                <b-field label="Upload experiment plan">
                                    <b-field class="file is-primary"  :class="{'has-name': !!experiment_plan_file}">
                                        <b-upload v-model="experiment_plan_file" class="file-label" rounded>
                                            <span class="file-cta">
                                                <b-icon class="file-icon" icon="upload"></b-icon>
                                                <span class="file-label">Click to upload</span>
                                            </span>
                                            <span class="file-name" v-if="experiment_plan_file">
                                                {{ experiment_plan_file.name }}
                                            </span>
                                        </b-upload>
                                    </b-field>
                                </b-field>
                                <b-field
                                    label="Planned experiment"
                                    v-if="experiment_plan">
                                    <b-field>
                                        # samples: {{experiment_plan.sample_placeholders.length.toString()}}
                                    </b-field>
                                    <b-field>
                                        <b-button
                                            type="is-primary"
                                            @click="is_modal_sample_table_active=true;">
                                            <b-icon icon="fullscreen">
                                            </b-icon>
                                        </b-button>
                                    </b-field>
                                </b-field>
                                <!-- End of upload experiment plan -->
                                <div><br></div>
                                <!-- Sample attributes form -->
                                <MetaDataForm
                                    :key="sample_attributes_key"
                                    form_title="Sample attribute template"
                                    :default_template="sample_attributes_default_template"
                                    :initial_template="sample_attributes_template.length ? sample_attributes_template : null"
                                    :editable="true"
                                    :fillable="false"
                                    :template_path="sample_attributes_template_path"
                                    @metaDataUpdated="sample_attributes_fields=$event">
                                </MetaDataForm>
                                <!-- End of sample attributes form -->
                            </section>
                        </div>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button 
                            @click="saveExperiment()">
                            Save
                        </b-button>
                        <b-button 
                            @click="cancelNewExperiment()">
                            Cancel
                        </b-button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of new experiment modal-->

        <!--- Edit experiment modal--> 
        <section class="experiment-attribute-modal">
            <b-modal :active.sync="is_modal_experiment_attributes_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px">
                    <div class="columns">
                        <div class="column">
                            <header class="modal-card-head">
                                <p class="modal-card-title">
                                    Edit experiment
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <MetaDataForm
                                    form_title="Experiment attributes"
                                    :initial_template="experiment_edit_form_props.attributes"
                                    :editable="true"
                                    @metaDataUpdated="experiment_attributes_fields=$event">
                                </MetaDataForm>
                                <div><br></div>
                                <MetaDataForm
                                    form_title="Sample attribute template"
                                    :initial_template="experiment_edit_form_props.sample_attributes_template"
                                    :editable="false"
                                    :fillable="false">
                                </MetaDataForm>
                            </section>
                        </div>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button 
                            :disabled="false"
                            @click="saveExperiment()">
                            Save
                        </b-button>
                        <b-button 
                            @click="is_modal_experiment_attributes_active=false">
                            Cancel
                        </b-button>
                        <div style="position:absolute; right:20px">
                            <b-button
                                @click="launchPrefillSampleAttributesModal()">
                                Prefill
                            </b-button>
                            <b-tooltip
                                label="Delete experiment"
                                position="is-left"
                                :delay="1000">
                                <b-button
                                    type="is-danger"
                                    icon-left="delete"
                                    @click="deleteExperiment(experiment_edit_form_props.attributes[0].value)">
                                </b-button>
                            </b-tooltip>
                        </div>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of edit experiment modal-->

        <!-- Modal for sample attributes -->
        <section class="sample-attribute-modal">
            <b-modal :active.sync="is_modal_sample_attributes_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="true"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">{{ sample_form_props.filename }}</p>
                        </header>
                        <section class="modal-card-body write_sample_attribute">                            
                            
                            <MetaDataForm
                                :key="sample_form_key"
                                :form_title="sample_form_props.title"
                                :default_template="sample_form_props.attributes"
                                :initial_template="sample_form_props.attributes"
                                :load_template_path="sample_form_props.load_template_path"
                                @metaDataUpdated="sample_attributes_fields=$event">
                            </MetaDataForm>

                            <div><br></div>
                            <b-field label="Project">
                                <b-select
                                    placeholder="Select a project"
                                    v-model="project_selected.title"
                                    @input="selectProject($event)"
                                    :disabled="autosave_on"
                                    required
                                    expanded>
                                    <option
                                        v-for="p in projects"
                                        :value="p.title"
                                        :key="p.title">
                                        {{ p.title }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    v-model="experiment_selected.title"
                                    @input="selectExperiment($event)"
                                    :disabled="autosave_on"
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments"
                                        :value="e.title"
                                        :key="e.title">
                                        {{ e.title }}
                                    </option>
                                </b-select>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                :type="sample_attributes_save_button_type"
                                @click="saveSample()"
                                :disabled="false">
                                Save
                            </b-button>
                            <b-button
                                @click="is_modal_sample_attributes_active=false">
                                Close
                            </b-button>
                            <div style="position:absolute; right:20px">
                                <b-tooltip
                                    label="Remove sample from this experiment"
                                    position="is-left"
                                    :delay="1000">
                                    <b-button
                                        type="is-danger"
                                        icon-left="delete"
                                        @click="removeSample(sample_form_props.filename)">
                                    </b-button>
                                </b-tooltip>
                            </div>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of Modal for sample edit -->

        <!-- Modal for prefilling sample attributes -->
        <section class="sample-attribute-modal">
            <b-modal :active.sync="is_modal_prefill_sample_attributes_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="true">
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">Prefill sample information</p>
                        </header>
                        <section class="modal-card-body write_sample_attribute">                            
                            
                            <MetaDataForm
                                form_title="Prefill sample attributes"
                                :initial_template="experiment_edit_form_props.sample_attributes_template"
                                :template_path="experiment_edit_form_props.prefilled_templates_path">
                            </MetaDataForm>

                            <div><br></div>
                            <b-field label="Project">
                                <b-select
                                    placeholder="Select a project"
                                    v-model="project_selected.title"
                                    @input="selectProject($event)"
                                    disabled
                                    required
                                    expanded>
                                    <option
                                        v-for="p in projects"
                                        :value="p.title"
                                        :key="p.title">
                                        {{ p.title }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    v-model="experiment_selected.title"
                                    @input="selectExperiment($event)"
                                    disabled
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments"
                                        :value="e.title"
                                        :key="e.title">
                                        {{ e.title }}
                                    </option>
                                </b-select>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                @click="is_modal_prefill_sample_attributes_active=false">
                                Close
                            </b-button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of modal for prefilling sample edit -->

        <!-- Sample table modal -->
        <section class="sample-table-modal">
            <b-modal :active.sync="is_modal_sample_table_active"
                full-screen
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="false"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card">
                    <header class="modal-card-head">
                        <p class="modal-card-title">
                            {{project_selected.title}}: {{experiment_selected.title}}
                        </p>
                        <!-- Column visibility dropdown -->
                        <b-dropdown
                            aria-role="menu"
                            type="is-dark"
                            position="is-bottom-right"
                            style="top:0px;"
                            trap-focus
                            multiple
                            append-to-body>
                            <b-button
                                icon-left="menu"
                                slot="trigger"
                                outlined>
                            </b-button>
                            <div>
                                <div v-for="(col, i) in sample_table_cols"
                                    :key="i"
                                    class="control">
                                    <b-checkbox
                                        v-model="col.visible"
                                        size="is-small">
                                        {{ col.label }}
                                    </b-checkbox>
                                </div>
                            </div>
                        </b-dropdown>
                        <!-- Close button -->
                        <b-button
                            icon-left="close"
                            @click="is_modal_sample_table_active=false"
                            is-dark>
                        </b-button>
                    </header>

                    <section class="modal-card-body">
                        <!-- Sample table -->
                        <b-table 
                            id="samples-datatable"
                            :height="760"
                            :data="sample_table_rows"
                            :sticky-header="true"
                            striped>
                            <!-- Columns -->
                            <b-table-column
                                v-for="(col, i) in sample_table_cols"
                                :key="i"
                                :field="col.field"
                                :label="col.label"
                                searchable
                                sortable
                                :visible="col.visible === null ? true : col.visible"
                                v-slot="props">
                                {{ props.row[col.field] }}
                            </b-table-column>
                            <!-- End of columns -->
                        </b-table>
                        <!-- End of sample table -->
                    </section>
                    <footer class="modal-card-foot">
                        <b-button
                            @click="exportSampleTable()">
                            Export CSV
                        </b-button>
                    </footer>
                </div>
            </b-modal>
        </section>     
        <!-- End of sample table modal -->

        <!-- Modal for sample import -->
        <section class="sample-import-modal">
            <b-modal :active.sync="is_modal_sample_import_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: 500px; height: 700px">
                        <header class="modal-card-head">
                            <p class="modal-card-title">Import samples</p>
                        </header>
                        <section class="modal-card-body">
                            <b-table 
                                id="import-sample-table"
                                :columns="import_sample_table_cols"
                                :data="import_sample_table_rows"
                                :checkable="true"
                                :header-checkable="false"
                                :checked-rows.sync="import_sample_table_checked_rows">
                            </b-table>
                            <div><br></div>
                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                @click="importSamples()"
                                is-dark
                                :disabled="!import_sample_table_checked_rows.length">
                                Import
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_modal_sample_import_active=false">
                                Cancel
                            </button>
                        </footer>
                    </div>
                </div>
            <b-loading
                :is-full-page="false"
                v-model="import_sample_table_loading">
            </b-loading>
            </b-modal>
        </section>
        <!-- End of sample import modal -->
    <!-- End of modals -->

    <!-- Main content area -->
        <section>
            <b-notification
                :active="autosave_on"
                :closable="false"
                type="is-danger"
                role="alert">
                <p style="font-size:16px">
                    Auto-save into {{project_selected.title}} / {{experiment_selected.title}}
                </p>
            </b-notification>
            <!-- Samples datatable collapsable -->
            <section>
                <b-collapse class="card" animation="slide" aria-id="contentIdForA11y3">
                    <div
                        slot="trigger" 
                        slot-scope="props"
                        class="card-header"
                        role="button"
                        aria-controls="contentIdForA11y3">
                        <p class="card-header-title">
                            Samples
                        </p>
                        <a class="card-header-icon">
                        <b-icon
                            :icon="props.open ? 'menu-down' : 'menu-up'">
                        </b-icon>
                        </a>
                    </div>
                    <div class="card-content">
                        <div class="content">
                            <div class="left-panel-collapsable">
                                <!-- Sample browser tree -->
                                <b-menu>
                                    <!-- Projects -->
                                    <b-menu-list label="Projects">
                                        <!-- Project item -->
                                        <b-menu-item
                                            v-for="p in projects"
                                            :key="p.title"
                                            :active.sync="p.active"
                                            :expanded.sync="p.active"
                                            @click="selectProject(p.title)"
                                            :disabled="autosave_on">
                                            <template #label>
                                                 <b-tooltip
                                                    :delay=500
                                                    position="is-right"
                                                    type="is-light"
                                                    multilined
                                                    append-to-body>
                                                    <!-- Menu item content -->
                                                    <div :id="p.title"
                                                        @contextmenu.prevent="rightClickProject($event)">
                                                        {{p.title}}
                                                    </div>
                                                    <template v-slot:content>
                                                        <!-- Tooltip html content -->
                                                        <div
                                                            v-html="prettyPrintAttributes(p.attributes)"
                                                            style="text-align:center;">
                                                        </div>
                                                    </template>
                                                </b-tooltip>
                                            </template>
                                            <!-- Experiments -->
                                            <b-menu-list
                                                label="Experiments"
                                                v-if="p.title === project_selected.title">
                                                <!-- Experiment item -->
                                                <b-menu-item 
                                                    v-for="e in experiments"
                                                    :key="e.title"
                                                    :active.sync="e.active"
                                                    :expanded.sync="e.active"
                                                    @click="selectExperiment(e.title)"
                                                    :disabled="autosave_on">
                                                    <template #label>
                                                        <b-tooltip
                                                            :delay=500
                                                            position="is-right"
                                                            type="is-light"
                                                            multilined
                                                            append-to-body>
                                                            <!-- Menu item content -->
                                                            <div :id="e.title"
                                                                @contextmenu.prevent="rightClickExperiment($event)">
                                                                {{e.title}}
                                                                <!-- <b-icon
                                                                    class="is-pulled-right"
                                                                    icon="fullscreen"
                                                                    @click.native="is_modal_sample_table_active=true">
                                                                </b-icon> -->
                                                            </div>
                                                            <template v-slot:content>
                                                                <!-- Tooltip html content -->
                                                                <div
                                                                    v-html="prettyPrintAttributes(e.attributes)"
                                                                    style="text-align:center;">
                                                                </div>
                                                            </template>
                                                        </b-tooltip>
                                                    </template>
                                                    <p class="menu-label">
                                                        Samples
                                                    </p>
                                                    <!-- Sample table -->
                                                    <!-- Buttons above table -->
                                                    <div class="columns">
                                                        <div class="column" style="text-align:left;">
                                                            <b-button
                                                                disabled
                                                                icon-left="plus"
                                                                class="tag is-dark"
                                                                outlined
                                                                @click="launchSampleImport()">
                                                            </b-button>
                                                        </div>
                                                        <div class="column" style="text-align:right;">
                                                            <b-button
                                                                icon-left="fullscreen"
                                                                class="tag is-dark"
                                                                outlined
                                                                @click="is_modal_sample_table_active=true">
                                                            </b-button>
                                                            <b-dropdown
                                                                aria-role="menu"
                                                                type="is-dark"
                                                                position="is-bottom-right"
                                                                style="top:0px;"
                                                                trap-focus
                                                                multiple
                                                                append-to-body>
                                                                <b-button
                                                                    icon-left="menu"
                                                                    class="tag is-dark"
                                                                    slot="trigger"
                                                                    outlined>
                                                                </b-button>
                                                                <div>
                                                                    <div v-for="(col, i) in sample_table_cols"
                                                                        :key="i"
                                                                        class="control">
                                                                        <b-checkbox
                                                                            v-model="col.visible"
                                                                            size="is-small">
                                                                            {{ col.label }}
                                                                        </b-checkbox>
                                                                    </div>
                                                                </div>
                                                            </b-dropdown>
                                                        </div>
                                                    </div>
                                                    <!-- End of buttons above table -->
                                                    <!-- Sample table -->
                                                    <b-table 
                                                        id="samples-datatable"
                                                        style="height:100%; width:100%"
                                                        :data="sample_table_rows"
                                                        :sticky-header="true"
                                                        :checkable="true"
                                                        :is-row-checkable="(row) => (row.filename && row.filename.indexOf('placeholder')==-1)"
                                                        :header-checkable="false"
                                                        :checked-rows.sync="sample_table_checked_rows"
                                                        :selected="sample_table_selected_row"
                                                        v-if="e.title === experiment_selected.title">
                                                        <!-- Columns -->
                                                        <b-table-column
                                                            v-for="(col, i) in sample_table_cols"
                                                            :key="i"
                                                            :field="col.field"
                                                            :label="col.label"
                                                            :visible="col.visible || false"
                                                            v-slot="props">
                                                            <a @click="rightClickSample(props.row.filename)">
                                                                <b-tooltip
                                                                    :delay=500
                                                                    position="is-right"
                                                                    type="is-light"
                                                                    multilined
                                                                    append-to-body>
                                                                {{ props.row[col.field] }}
                                                                <template v-slot:content>
                                                                    <!-- Tooltip html content -->
                                                                    <div
                                                                        v-html="prettyPrintAttributes(getSample(props.row.filename).attributes)"
                                                                        style="text-align:center;">
                                                                    </div>
                                                                </template>
                                                                </b-tooltip>
                                                            </a>
                                                        </b-table-column>
                                                        <!-- End of columns -->
                                                    </b-table>
                                                    <!-- End of sample table -->
                                                    <!-- End of import sample item -->
                                                </b-menu-item>
                                                <!-- End of experiment item -->
                                                <!-- New experiment item -->
                                                <b-menu-item
                                                    icon="plus"
                                                    :active="is_modal_new_experiment_active"
                                                    @click="launchNewExperimentModal()"
                                                    :disabled="autosave_on">
                                                </b-menu-item>
                                                <!-- End of new experiment item -->
                                            </b-menu-list>
                                            <!-- End of experiments -->
                                        </b-menu-item>
                                        <!-- End of project item -->
                                        <!-- New project item -->
                                        <b-menu-item
                                            icon="plus"
                                            :active="is_modal_project_attributes_active"
                                            @click="launchProjectAttributesModal('new')"
                                            :disabled="autosave_on">
                                        </b-menu-item>
                                        <!-- End of new project item -->
                                    </b-menu-list>
                                    <!-- End of projects -->
                                </b-menu>
                                <!-- End of sample browser tree -->
                            </div>
                        </div>
                    </div>
                </b-collapse>
            </section>
            <!-- End of Sample datatable collapable -->
        </section>
    <!-- End of main content area -->
    </div>
</template>


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from 'vuex'
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';
import { BECom, isValidFilename, shallow_copy } from "../karsalib.js"
import MetaDataForm from "./MetaDataForm.vue"

Vue.use([Buefy]);

const _ = require('underscore');
const fs = require('fs');
const { Parser } = require('json2csv');

export default {
    name: "SampleBrowser",
    components: {
        MetaDataForm,
    },
    props: {
    },
    computed: {
        ...mapState([
            'autosave_on',
            'new_file',
            'root_namespace',
        ]),

        experiments: {
            get() {
                return this.$store.state.experiments;
            },
            set(value) {
                this.$store.commit('experiments', value);
            }
        },
        experiment_selected: {
            get() {
                return this.$store.state.experiment_selected;
            },
            set(value) {
                this.$store.commit('experiment_selected', value);
            }
        },
        projects: {
            get() {
                return this.$store.state.projects;
            },
            set(value) {
                this.$store.commit('projects', value);
            }
        },
        project_selected: {
            get() {
                return this.$store.state.project_selected;
            },
            set(value) {
                this.$store.commit('project_selected', value);
            }
        },
        sample_annotations: {
            get() {
                return this.$store.state.sample_annotations;
            },
            set(value) {
                this.$store.commit('sample_annotations', value);
            }
        },
        sample_selected: {
            get() {
                return this.$store.state.sample_selected;
            },
            set(value) {
                this.$store.commit('sample_selected', value);
            }
        },
    },
    data: function() {
        return {
            // Communication
            be: null,
            namespace: null,
            room_experiment: null,
            room_project: null,
            room_sid: null,
            endpoints: [
                'experiments',
                'importable_samples',
                'projects',
                'samples',
            ],
            // acquisition_started: false,
            // Project / experiment title validation
            // Modal active variables
            is_modal_landing_active: true,
            is_modal_experiment_attributes_active: false,
            is_modal_prefill_sample_attributes_active: false,
            is_modal_project_attributes_active: false,
            is_modal_new_experiment_active: false,
            is_modal_sample_import_active: false,
            is_modal_sample_attributes_active: false,
            is_modal_sample_table_active: false,
            // variables for import modals
            import_start_time: null,
            import_end_time: null,
            import_min_datetime: null,
            import_max_datetime: new Date(),
            // variables for sample import modal
            importable_samples: {},
            import_sample_table_loading: true,
            import_sample_table_rows: [],
            import_sample_table_cols: [],
            import_sample_table_checked_rows: [],
            import_sample_table_datetime_range: {},
            // Project metadata
            project_attributes_default_template: [
                {'label': "Title",
                 'value': "",
                 'required': true},
                {'label': "Description",
                 'value': ""},
            ],
            project_attributes_fields: [],
            project_attributes_template_path: "./metadata_templates/project_templates",
            project_form_props: {},

            // Experiment metadata
            experiment_attributes_default_template: [
                {'label': "Title",
                 'value': "",
                 'required': true},
                {'label': "Description",
                 'value': ""},
            ],
            experiment_attributes_fields: [],
            experiment_attributes_template_path: "./metadata_templates/experiment_templates",
            experiment_edit_form_props: {},
            experiment_plan: null,
            experiment_plan_blob: "",
            experiment_plan_file: {},
            // Sample metadata for selected sample
            samples: [],
            // variables for sample table
            sample_table_rows: [],
            sample_table_cols: [],
            sample_table_checked_rows: [],
            sample_table_selected_row: {},
            sample_attributes: {},
            sample_attributes_default_template: [
                {'label': "Title",
                 'value': "",
                 'required': true},
                {'label': "Description",
                 'value': ""},
            ],
            sample_attributes_fields: [],
            sample_attributes_key: Math.random(),
            sample_attributes_save_button_type: "is-success",
            sample_attributes_template: [],
            sample_attributes_template_path: "./metadata_templates/sample_templates",
            sample_form_key: Math.random(),
            sample_form_props: {},
        }
    },
    created: function() {
        this.be = new BECom(this);
    },
    mounted: function() {
    },
    methods: {
        log: function(...args) {
            console.log('[' + this.name + ']',  ...args);
        },
        addSampleTableCol() {
            // TODO: add column when target is added
            return
        },
        addSampleTableRow() {
            // TODO: On new sample, add row instead of full table update
            return
        },
        cancelNewExperiment() {
            this.resetExperimentPlan();
            this.is_modal_new_experiment_active = false;
        },
        cancelNewProject() {
            this.is_modal_project_attributes_active = false;
        },
        deleteExperiment(title) {
            this.is_modal_experiment_attributes_active = false;
            const experiment_to_delete = this.getExperiment(title);
            return this.be.export_one_way_binding_prop(
                                            'delete_experiment',
                                            {'project': experiment_to_delete.project,
                                             'experiment': experiment_to_delete.title},
                                            );
        },
        deleteProject(title) {
            this.is_modal_project_attributes_active = false;
            return this.be.export_one_way_binding_prop(
                                            'delete_project',
                                            {'project': title},
                                            );
        },
        exportSampleTable() {
            const fields = this.sample_table_cols.map(a => { return {'label': a.label, 'value': a.field } });
            const opts = {
                "fields": fields,
            };

            try {
                // Parse CSV
                const parser = new Parser(opts);
                const csv = parser.parse(this.sample_table_rows);
                const csv_filename = this.project_selected.title + '_' + this.experiment_selected.title + '.csv';
                // Make blob
                const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                // Create a temporary download link for the blob and "click" it
                var link = document.createElement('a');
                var url = URL.createObjectURL(blob);
                link.setAttribute('href', url);
                link.setAttribute('download', csv_filename);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                // Remove the link
                document.body.removeChild(link);
            } catch (err) {
                console.error(err);
            }

        },
        getExperiment(experiment_title) {
            for (let i in this.experiments) {
                if(this.experiments[i].title === experiment_title){
                    return shallow_copy(this.experiments[i]);
                }
            }
            return {'title': "",
                    'attributes': [],
                    };
        },
        getPrefilledTemplatePath(project_title, experiment_title, make_if_missing=false) {
            const template_path = "./metadata_templates/prefilled_templates/" + ([project_title, experiment_title].join("_"));
            if (!fs.existsSync(template_path)) {
                if (make_if_missing) {
                    fs.mkdirSync(template_path);
                } else {
                    return null
                }
            }
            return template_path
        },
        getProject(project_title) {
            for (let i in this.projects) {
                if(this.projects[i].title === project_title){
                    return shallow_copy(this.projects[i]);
                }
            }
            return {'title': "",
                    'attributes': [],
                    };
        },
        getSample(sample_filename) {
            return shallow_copy({
                            'filename': sample_filename,
                            ...this.samples[sample_filename]
                            });
        },
        importSamples() {
            // TODO: Needs an update

            let to_import = this.import_sample_table_checked_rows[0];
            // Preserve sample id, title and description
            // Set project and experiment to the selected ones
            let sample = {
                'title': to_import.title,
                'experiment': this.experiment_selected.title,
                'project': this.project_selected.title,
                'attributes': {
                    'title': to_import.title,
                    'description': to_import.description,
                    }
                };
            // Export sample attributes to link into current experiment
            this.sample_attributes = sample;
            this.is_modal_sample_import_active = false;
        },
        launchExperimentAttributesModal(experiment) {
            this.experiment_edit_form_props = {};
            this.experiment_edit_form_props.project = experiment.project;
            this.experiment_edit_form_props.experiment = experiment.title;
            this.experiment_edit_form_props.attributes = experiment.attributes;
            this.experiment_edit_form_props.sample_attributes_template = experiment.sample_attributes_template;
            this.is_modal_experiment_attributes_active = true;
        },
        launchNewExperimentModal() {
            this.is_modal_new_experiment_active = true;
        },
        launchPrefillSampleAttributesModal() {
            const experiment_title = this.experiment_edit_form_props.experiment;
            const project = this.experiment_edit_form_props.project;
            this.experiment_edit_form_props.prefilled_templates_path = this.getPrefilledTemplatePath(project, experiment_title, true);
            this.is_modal_prefill_sample_attributes_active = true;
        },
        launchProjectAttributesModal(mode, initial_template=null) {
            switch (mode) {
                case "new":
                    this.project_form_props = {
                        'title': "New Project",
                        'initial_template': initial_template,
                        'default_template': this.project_attributes_default_template,
                        'editable': true,
                        'template_path': this.project_attributes_template_path,
                    };
                    break;
                case "edit":
                    this.project_form_props = {
                        'title': "Edit project",
                        'initial_template': initial_template,
                        'default_template': [],
                        'editable': true,
                        'template_path': null,
                    };
                    break;
            }
            this.is_modal_project_attributes_active = true;
        },
        launchSampleAttributeModal() {
            this.is_modal_sample_attributes_active = true;
        },
        launchSampleImport() {
            // Request list of samples from FileService
            this.import_sample_table_datetime_range = Math.random();
            // Set loading state
            this.import_sample_table_loading = true;
            // Launch modal
            this.is_modal_sample_import_active = true;
        },
        prettyPrintAttributes(form_fields) {
            let pretty_text = "";
            for (let i in form_fields) {
                let label = form_fields[i].label;
                let value = form_fields[i].value;
                pretty_text += ("<b>"+label+"</b>"+"<br>" + value + "<br>");
            }
            return pretty_text
        },
        removeSample(filename) {
            this.is_modal_sample_attributes_active = false;
            const sample_to_remove = this.getSample(filename);
            return this.be.export_one_way_binding_prop(
                                            'delete_sample',
                                            sample_to_remove,
                                            );
        },
        resetExperimentPlan() {
            this.experiment_plan = null;
            this.experiment_plan_blob = "";
            this.experiment_plan_file = {};
            this.samples = [];
            this.sample_attributes_template = shallow_copy(this.sample_attributes_default_template);
        },
        rightClickExperiment(event) {
            const title = event.path[0].id;
            let experiment = this.getExperiment(title);
            // Disabled title editing
            experiment.attributes[0].disabled = true;
            this.launchExperimentAttributesModal(experiment);
        },
        rightClickProject(event) {
            const title = event.path[0].id;
            let project = this.getProject(title);
            // Disabled title editing
            project.attributes[0].disabled = true;
            this.launchProjectAttributesModal('edit', project.attributes);
        },
        rightClickSample(sample_filename) {
            const sample = this.getSample(sample_filename);
            this.sample_form_props = sample;
            this.sample_form_props.title = "Edit sample attributes";
            this.launchSampleAttributeModal();
        },
        saveExperiment() {
            let title = this.experiment_attributes_fields[0].value;
            if ( !isValidFilename(title) ) {
                // Title contains illegal characters
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "The title must contain only numbers, letters and _",
                    type: 'is-danger'
                });
                return
            }
            const new_experiment = {
                    'title': title,
                    'project': this.project_selected.title,
                    'attributes': this.experiment_attributes_fields,
                    'sample_attributes_template': this.sample_attributes_fields,
                    'sample_placeholders': this.experiment_plan ? this.experiment_plan.sample_placeholders : [],
                    };
            
            this.be.export_one_way_binding_prop('save_experiment',
                                                new_experiment,
                                                );
            this.experiment_selected = new_experiment;
            this.resetExperimentPlan();
            this.is_modal_new_experiment_active = false;
        },
        saveProject() {
            let title = this.project_attributes_fields[0].value;
            if ( !isValidFilename(title) ) {
                // Title contains illegal characters
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "The title must contain only numbers, letters and _",
                    type: 'is-danger'
                });
                return
            }
            const new_project = {
                    'title': title,
                    'attributes': this.project_attributes_fields
                    };
            this.project_selected = new_project;
            this.is_modal_project_attributes_active = false;
            return this.be.export_one_way_binding_prop('save_project',
                                                        new_project,
                                                        );
        },
        saveSample() {
            if ( !(this.project_selected.title.length && this.experiment_selected.title.length) ) {
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "Project and experiment must be selected to store sample attributes.",
                    type: 'is-danger'
                })
                return
            }
            let sample_to_save = {
                'filename': this.sample_form_props.filename,
                'experiment': this.sample_form_props.experiment,
                'project': this.sample_form_props.project,
                'attributes': this.sample_attributes_fields,
                'method': this.sample_form_props.method,
            };
            // this.sample_attributes = sample;
            this.is_modal_sample_attributes_active = false;
            return this.be.export_one_way_binding_prop('save_sample',
                                                       sample_to_save,
                                                       );
        },
        selectExperiment(experiment_title) {
            // if (experiment_title === this.experiment_selected.title) {
            //     return
            // }
            // Set experiment active in sample tree
            for (let i in this.experiments) {
                if(this.experiments[i].title === experiment_title){
                    this.experiments[i].active = true;
                } else {
                    this.experiments[i].active = false;
                }
            }
            if (this.experiment_selected.title != experiment_title) {
                this.experiment_selected = this.getExperiment(experiment_title);
            }
            this.is_modal_new_experiment_active = false;
            this.is_modal_experiment_attributes_active = false;
            this.is_modal_landing_active = false;
        },
        selectProject(project_title) {
            // if (project_title === this.project_selected.title) {
            //     return
            // }
            // Set project active in the sample tree
            for (let i in this.projects) {
                if(this.projects[i].title === project_title){
                    this.projects[i].active = true;
                } else {
                    this.projects[i].active = false;
                }
            }
            this.project_selected = shallow_copy(this.getProject(project_title));
            if (this.project_selected.title !== this.experiment_selected.project) {
                // Reset experiment
                this.experiment_selected = {
                    'title': "",
                    'project': "",
                    'attributes': [],
                    'sample_attributes_template': [],
                    };
            }
            this.is_modal_project_attributes_active = false;
        },
    },
    watch: {
        experiment_selected: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if ( !_.isEmpty(new_value.title) ) {
                if ( !_.isEmpty(this.room_experiment) )
                    this.be.unsubscribe(['samples'],
                                        this.room_experiment
                                        );
                this.room_experiment = this.project_selected.title + '_' + new_value.title;
                this.be.subscribe(['samples'],
                                  this.room_experiment
                                  );
                this.be.export_one_way_binding_prop('experiment_selected',
                                                    new_value,
                                                    old_value,
                                                    this.room_sid
                                                    );
                if (this.is_modal_sample_attributes_active) {
                    // Update sample form props
                    this.sample_form_props = shallow_copy(this.sample_form_props);
                    this.sample_form_props.load_template_path = this.getPrefilledTemplatePath(this.project_selected.title, this.experiment_selected.title);
                    this.sample_form_props.project = this.project_selected.title;
                    this.sample_form_props.experiment = this.experiment_selected.title;
                    let sample_attributes = shallow_copy(this.experiment_selected.sample_attributes_template);
                    // Set title prefix
                    let sample_no = this.samples.length + 1;
                    const sample_title_prefix = sample_no.toString().padStart(3, '0') + '_';
                    sample_attributes[0].value = sample_title_prefix;
                    this.sample_form_props.attributes = sample_attributes;
                    this.sample_attributes_fields = sample_attributes;
                    this.sample_form_key = Math.random();
                }
            }
        },
        experiment_plan: function(new_value) {
            if (new_value) {
                this.sample_attributes_template = new_value.sample_attributes_template;
                this.sample_attributes_key = Math.random();
                this.samples = new_value.sample_placeholders;
            }
        },
        experiment_plan_blob: function(new_value) {
            if (new_value) {
                return this.be.export_one_way_binding_prop('parse_experiment_plan_blob',
                                                        new_value,
                                                        );
            }
        },
        experiment_plan_file: async function(new_value) {
            if (!new_value.text) {
                return
            }
            let file_content = await new_value.text();
            this.experiment_plan_blob = file_content;
        },
        experiments: function() {
            if (this.experiment_selected.title) {
                this.selectExperiment(this.experiment_selected.title);
            }
        },
        import_sample_table_datetime_range: function(new_value, old_value) {
            return this.be.export_one_way_binding_prop('import_sample_table_datetime_range',
                                                        new_value, old_value,
                                                        this.room_experiment);
        },
        import_sample_table_checked_rows: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            var last_selection = [...new_value].pop();
            // force single row selection
            if ( this.import_sample_table_checked_rows.length > 1 ) {
                this.import_sample_table_checked_rows = [last_selection,];
            }
        },
        importable_samples: function(new_data){
            for (let i=0; i<new_data.cols.length; i++) {
                new_data.cols[i]['searchable'] = true;
            }
            this.import_sample_table_cols = new_data.cols;
            this.import_sample_table_rows = new_data.rows;
            this.import_sample_table_loading = false;
        },
        new_file: function(new_value) {
            this.$buefy.toast.open({
                duration: 5000,
                message: 'Acquisition started: ' + new_value.filename,
                type: 'is-success'
            })

            this.sample_table_selected_row = {};

            this.sample_form_props = {};
            this.sample_form_props.title = "New sample attributes";
            this.sample_form_props.load_template_path = this.getPrefilledTemplatePath(this.project_selected.title, this.experiment_selected.title);
            this.sample_form_props.filename = new_value.filename;
            this.sample_form_props.method = new_value.method;
            this.sample_form_props.project = this.project_selected.title;
            this.sample_form_props.experiment = this.experiment_selected.title;
            
            // Initialize sample attribute fields
            this.sample_attributes_fields = shallow_copy(this.experiment_selected.sample_attributes_template);

            if (this.autosave_on) {
                // Auto-save sample
                for (let sample_id in this.samples) {
                    // Find first placeholder sample
                    if (sample_id.indexOf('placeholder') != -1) {
                        // Copy attributes from placeholder
                        this.sample_attributes_fields = shallow_copy(this.samples[sample_id].attributes);
                        // Delete placeholder
                        this.removeSample(sample_id);
                        break
                    }
                }
                // Save sample
                this.saveSample();
            } else {
                // Manual sample info input
                // Set title prefix
                let sample_attributes = this.sample_attributes_fields;
                let sample_no = Object.keys(this.samples).length + 1;
                const sample_title_prefix = sample_no.toString().padStart(3, '0') + '_';
                sample_attributes[0].value = sample_title_prefix;
                this.sample_form_props.attributes = sample_attributes;
                this.sample_attributes_fields = sample_attributes;
                this.launchSampleAttributeModal();
            }   
        },
        project_selected: function(new_value, old_value) {
            if ( _.isEqual(new_value.title, old_value.title) ) {
                return false;
            }
            if ( !_.isEmpty(new_value.title) ) {
                if ( !_.isEmpty(this.room_project) ) {
                    this.be.unsubscribe(['experiments'],
                                        this.room_project
                                        );
                }
                this.room_project = new_value.title;
                this.be.subscribe(['experiments'],
                                  this.room_project
                                  );
                // push new_value of project_selected to corresponding room
                this.be.export_one_way_binding_prop('project_selected',
                                                    new_value,
                                                    old_value,
                                                    this.room_sid
                                                    );
            }
        },
        projects: function() {
            if (this.project_selected.title) {
                let experiment_selected_title = this.experiment_selected.title;
                this.selectProject(this.project_selected.title);
                if (experiment_selected_title)
                    this.selectExperiment(experiment_selected_title);
            }
        },
        samples: function(new_value){
            // Format data to sample table
            let samples = new_value;
            let rows = [];
            let cols = [];
            for (const sample_id in samples) {
                let sample = samples[sample_id];
                let row = {};
                // Unpack attributes
                for (let i in sample.attributes) {
                    let attr = sample.attributes[i];
                    if (rows.length == 0) {
                        let col = {
                            'field': attr.label.toLowerCase(),
                            'label': attr.label,
                            };
                        if (i == 0) {
                            col.visible = true;
                        }
                        cols.push(col);
                    }
                    row[attr.label.toLowerCase()] = attr.value;
                }
                // Unpack properties
                for (const prop in sample.properties) {
                    if (rows.length == 0) {
                        cols.push({
                            'field': prop.toLowerCase(),
                            'label': prop,
                            });
                    }
                    row[prop.toLowerCase()] = sample.properties[prop];
                }
                // Unpack method
                for (const par in sample.method) {
                    if (rows.length == 0) {
                        cols.push({
                            'field': par.toLowerCase(),
                            'label': par,
                            });
                    }
                    row[par.toLowerCase()] = sample.method[par];
                }
                // Project and experiment
                row['filename'] = sample_id
                row['project'] = sample.project;
                row['experiment'] = sample.experiment;
                if (rows.length == 0) {
                    cols = cols.concat([
                        {
                        'field': "filename",
                        'label': "Filename",
                        },
                        {
                        'field': "project",
                        'label': "Project",
                        },
                        {
                        'field': "experiment",
                        'label': "Experiment",
                        }
                    ]);
                }
                rows.push(row);
                // Avoid losing sample selection on an update to sample table
                if (sample_id == this.sample_selected.filename) {
                    this.sample_table_checked_rows = [row,];
                }
                // Highlight sample being (or last) acquired
                if (sample_id == this.new_file.filename) {
                    this.sample_table_selected_row = row;
                }
            }
            this.sample_table_cols = cols;
            this.sample_table_rows = rows;
        },
        sample_table_checked_rows: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            var last_selection = [...new_value].pop();
            // sample_table_checked_rows manipulates multi-row selection,
            // but by design limitation, it should be a single row selection
            if ( this.sample_table_checked_rows.length > 1 ) {
                this.sample_table_checked_rows = [last_selection,];
            }
            if (last_selection) {
                // Sample selected
                let filename = last_selection.filename;
                const sample = this.getSample(filename);
                this.sample_selected = {'title': last_selection.title,
                                        ...sample
                                        };
            } else {
                // Sample deselected
                this.sample_selected = {
                            'filename': "",
                            'title': "",
                            'properties': {
                                'length': 0,
                                'range': [0, 0],
                                },
                            };
            }
            this.sample_annotations = [];
        },
        'root_namespace.connected': function(new_value) {
            if ( new_value === true )
            {
                this.namespace = this.root_namespace;
                // handlers for for external notifications:
                this.namespace.on('experiment_plan', (value) => this.be.import_one_way_binding_prop('experiment_plan', value.value));
                this.namespace.on('experiments', (value) => this.be.import_two_way_binding_prop('experiments', value.value));
                this.namespace.on("importable_samples", (value) => this.be.import_one_way_binding_prop("importable_samples", value.value));
                this.namespace.on("projects", (value) => this.be.import_two_way_binding_prop("projects", value.value));
                this.namespace.on("samples", (value) => this.be.import_one_way_binding_prop("samples", value.value));

                this.room_sid = this.root_namespace.id;
                this.be.subscribe(this.endpoints, this.room_sid);
                this.be.subscribe(['projects'], 'projects');
            }
        },
    }
};


</script>
