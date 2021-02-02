<template>
    <div class="columns" id="measurement-tab-contents">
        <!--- All modals or popups should be here--> 

        <!-- Modal for edit temperature ramp datatable values -->
        <section class="modal-edit-temperature-ramp-data-table-row">
            <b-modal :active.sync="is_edit_temperature_ramp_modal_active"
                has-modal-card
                trap-focus
                aria-role="dialog"
                aria-modal
            >
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <!-- <header class="modal-card-head">
                            <p class="modal-card-title">Scenthound parameters</p>
                        </header> -->
                        <section class="modal-card-body idparams-edit-body">
                            <b-field label="t(s)">
                                <b-input
                                    v-model="edit_dialog_time"
                                    :value="edit_dialog_time"
                                    placeholder="seconds"
                                >
                                </b-input>
                            </b-field>

                            <b-field label="Temperature">
                                <b-input
                                    v-model="edit_dialog_temperature"
                                    :value="edit_dialog_temperature"
                                    placeholder="Temperature"
                                >
                                </b-input>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="edit_row_in_config_desorption_table()">
                                Save
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_edit_temperature_ramp_modal_active=false">
                                Close
                            </button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of Modal for edit temperature ramp datatable values -->

        <!-- Modal for sample attributes -->
        <section class="sample-attribute-modal">
            <b-modal :active.sync="is_sample_attribute_modal_active"
                has-modal-card
                trap-focus
                :can-cancel="false"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">{{ sample_file }}</p>
                        </header>
                        <section class="modal-card-body write_sample_attribute">
                            
                            <b-field label="Sample title">
                                <b-input type="input"
                                    v-model="sample_name"
                                    :value="sample_name"
                                    maxlength="50">
                                </b-input>
                            </b-field>

                            <b-field label="Description">
                                <b-input
                                    v-model="sample_description"
                                    :value="sample_description"
                                    maxlength="200"
                                    type="textarea">
                                </b-input>
                            </b-field>

                            <b-field label="Project">
                                <b-select
                                    placeholder="Select a project"
                                    v-model="sample_project"
                                    required
                                    expanded>
                                    <option
                                        v-for="p in projects"
                                        :value="p.id"
                                        :key="p.id">
                                        {{ p.id }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    v-model="sample_experiment"
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments"
                                        :value="e.id"
                                        :key="e.id">
                                        {{ e.id }}
                                    </option>
                                </b-select>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                @click="write_sample_attributes"
                                is-dark>
                                Save
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_sample_attribute_modal_active=false">
                                Close
                            </button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of Modal for sample edit -->

        <!-- Modal for h5 import -->
        <section class="h5-import-modal">
            <b-modal :active.sync="is_import_h5_modal_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: 500px; height: 700px">
                        <header class="modal-card-head">
                            <p class="modal-card-title">Import h5 files</p>
                        </header>
                        <section class="modal-card-body">
                            <b-field label="Start">
                                <b-datetimepicker
                                    v-model="import_start_time"
                                    placeholder="Start datetime"
                                    :timepicker="{'hour-format': '24'}"
                                    :min-datetime="import_min_datetime"
                                    :max-datetime="import_max_datetime">
                                </b-datetimepicker>
                            </b-field>
                            <b-field label="End">
                                <b-datetimepicker
                                    v-model="import_end_time"
                                    placeholder="End datetime"
                                    :timepicker="{'hour-format': '24'}"
                                    :min-datetime="import_start_time"
                                    :max-datetime="import_max_datetime">
                                </b-datetimepicker>
                            </b-field>
                            <button
                                class="button"
                                type="button"
                                @click="FetchH5s()"
                                is-dark
                                :disabled="(h5_streamer_status==='not_ready' ||
                                            import_start_time === null ||
                                            import_end_time === null
                                            ) ? true : false">
                                Fetch h5 list
                            </button>
                            <div><br></div>
                            <b-table 
                                id="h5-samples-table"
                                :columns="import_h5_table_cols"
                                :data="import_h5_table_rows"
                                :checkable="true"
                                :checked-rows.sync="import_h5_table_checked_rows">
                            </b-table>
                            <div><br></div>
                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                @click="ImportH5s()"
                                is-dark
                                :disabled="(!import_h5_table_checked_rows.length ||
                                            import_start_time === null ||
                                            import_end_time === null
                                            ) ? true : false">
                                Import
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_import_h5_modal_active=false">
                                Cancel
                            </button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of h5 import modal -->

        <!-- Modal for sample import -->
        <section class="sample-import-modal">
            <b-modal :active.sync="is_import_sample_modal_active"
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
                                @click="ImportSamples()"
                                is-dark
                                :disabled="!import_sample_table_checked_rows.length">
                                Import
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_import_sample_modal_active=false">
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

        <!-- Modal for Excel import -->
        <section class="excel-import-modal">
            <b-modal :active.sync="is_excel_clipboard_modal_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: 500px; height: 700px">
                        <header class="modal-card-head">
                            <p class="modal-card-title">Import from Excel clipboard</p>
                        </header>
                        <section class="modal-card-body" style="text-align: center">
                            <b-field label="Paste clipboard">
                                <b-input
                                    v-model="excel_clipboard_text"
                                    type="textarea">
                                </b-input>
                            </b-field>
                            <b-field label="Use first row as a header" >
                                <b-checkbox v-model="excel_clipboard_use_header" size="is-medium">
                                </b-checkbox>
                            </b-field>
                            <div><br></div>
                            <b-table 
                                id="excel-clipboard-table"
                                :columns="excel_clipboard_table_cols"
                                :data="excel_clipboard_table_rows">
                            </b-table>
                            <div><br></div>
                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                @click="ImportExcelTargets()"
                                is-dark>
                                Import
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_excel_clipboard_modal_active=false">
                                Cancel
                            </button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of sample import modal -->
        <!-- No modals below -->

        <!-- Main content  area-->
        <section class="main-content">
            <div class="columns">
                <!-- Left column -->
                <div class="column is-one-quarter">
                    <!-- scenthound status column --> 
                    <div class="acquisition-parameters" style="margin-bottom:0.4rem;">
                        <h2 class="acquisition-parameters-h2">
                            Scenthound status: {{ scenthound_status }}
                        </h2>
                    </div>
                    <!-- End of scenthound status column -->

                    <!-- Acquisiton and write sample button -->
                    <b-progress
                        v-bind:value="acquisition_progress"
                        show-value
                        format="percent"
                        :precision="1"
                        type="is-primary"
                        size="is-large">
                    </b-progress>
                    <!-- <div hidden> -->
                    <div class="acquisition-parameters"
                         style="margin-bottom:0.4rem;padding:10px;">
                        <b-field>
                            <b-button
                                v-bind:icon-left="acquisition_status=='starting' || 
                                                  acquisition_status=='stopping' ||
                                                  instrument_status=='not_ready' ? 'flattr' : ''"
                                :type="acquisition_button_type"
                                :disabled="acquisition_mode=='triggered' ||
                                           instrument_status=='not_ready'"
                                @click="on_button_change_acquisition_status()">
                                {{ acquisition_control_label }}
                            </b-button>
                        </b-field>
                    </div>
                    <!-- </div> -->
                    <!-- End of acquisiton and write sample button -->

                    <!-- Acquisiton parameters collapsable -->
<div hidden>
                    <section style="width:100%;">
                        <b-collapse
                            class="card"
                            animation="slide"
                            aria-id="contentIdForA11y3">
                            <div
                                slot="trigger" 
                                slot-scope="props"
                                class="card-header"
                                role="button"
                                aria-controls="contentIdForA11y3">
                                <p class="card-header-title">
                                    Acquisition Parameters
                                </p>
                                <a class="card-header-icon">
                                <b-icon
                                    :icon="props.open ? 'menu-down' : 'menu-up'">
                                </b-icon>
                                </a>
                            </div>
                            <div class="card-content">
                                <div class="content">
                                    <h1 class="acquisition-parameters-h1">
                                        Measurement Mode
                                    </h1>
                                    <div class="acquisition-parameters-form">
                                        <b-field grouped>
                                            <b-radio
                                                type="is-white"
                                                v-model="acquisition_mode"
                                                native-value="triggered">
                                                Triggered
                                            </b-radio>
                                            <b-radio
                                                type="is-white"
                                                v-model="acquisition_mode"
                                                native-value="continuous">
                                                Continuous
                                            </b-radio> 

                                            <label class="sample-length-label">
                                                Sample length(s)
                                            </label>
                                            <b-input
                                                class="sample-length"
                                                size="is-small"
                                                placeholder="90"
                                                v-model="sample_length"
                                                :value="sample_length"
                                                type="number"
                                                min="0"
                                                max="20000">
                                            </b-input>
                                        </b-field>
                                    </div>
                                    <!-- Desorption collapsable -->
                                    <section style="width:100%;padding:0.5rem;">
                                        <b-collapse
                                            class="inner-collapsable card"
                                            @open="draw_desorption_chart()"
                                            :open="false"
                                            animation="slide"
                                            aria-id="contentIdForA11y3">
                                            <div
                                                slot="trigger" 
                                                slot-scope="props"
                                                class="inner-collapsable card-header"
                                                role="button"
                                                aria-controls="contentIdForA11y3">
                                                <p class="card-header-title">
                                                    Desorption Temperature ramp
                                                </p>
                                                <a class="card-header-icon">
                                                <b-icon
                                                    :icon="props.open ? 'menu-down' : 'menu-up'">
                                                </b-icon>
                                                </a>
                                            </div>
                                            <div class="card-content">
                                                <div class="desorption-temperature-ramp-controls">
                                                    <b-button
                                                        icon-left="file-document-box-plus-outline"
                                                        size="is-small"
                                                        type="is-dark"
                                                        @click="show_add_new_row=true"
                                                        outlined
                                                        inverted> 
                                                    </b-button>
                                                    <b-button
                                                        icon-left="file-document-edit-outline"
                                                        size="is-small"
                                                        type="is-dark"
                                                        @click="show_desorption_edit_modal()"
                                                        v-if="desorption_table_selected_row !=null"
                                                        outlined
                                                        inverted>
                                                    </b-button>
                                                    <b-button
                                                        icon-left="trash-can-outline"
                                                        size="is-small"
                                                        type="is-dark"
                                                        @click="delete_row_in_config_desorption_table()"
                                                        v-if="desorption_table_selected_row !=null"
                                                        outlined
                                                        inverted>
                                                    </b-button>
                                                </div>
                                                <div
                                                    class="columns add-new-desorption-row"
                                                    v-if="show_add_new_row==true">
                                                    <div class="column" style="width:30%"> 
                                                        <b-input
                                                            size="is-small"
                                                            v-model="time"
                                                            type="number"
                                                            placeholder="time">
                                                        </b-input>
                                                    </div>
                                                    <div class="column" style="width:30%">
                                                        <b-input
                                                            size="is-small"
                                                            v-model="temperature"
                                                            type="number"
                                                            placeholder="temperature">
                                                        </b-input>
                                                    </div>
                                                    <div class="" style="width:40%; padding-top:15px;">
                                                        <b-button 
                                                            type="is-dark" 
                                                            size="is-small" 
                                                            @click="save_new_row_in_config_desorption_table()" 
                                                            outlined 
                                                            inverted>
                                                            Save
                                                        </b-button>
                                                        &nbsp; 
                                                        <b-button 
                                                            type="is-dark" 
                                                            size="is-small" 
                                                            @click="show_add_new_row=false;
                                                                    time=''; 
                                                                    temperature='';"
                                                            outlined 
                                                            inverted>
                                                            Cancel
                                                        </b-button>
                                                    </div>
                                                </div>
                                                <div class="">
                                                    <b-table
                                                        class="desorption-temperature-ramp-table desorption-data-table"
                                                        :data="desorption_table_data"
                                                        :columns="desorption_table_columns"
                                                        per-page="5"
                                                        current-page.sync="0"
                                                        :paginated="true" 
                                                        :pagination-simple="false"
                                                        :checked-rows.sync="desorption_table_checked_rows"
                                                        :selected.sync="desorption_table_selected_row"
                                                        checkable
                                                        sortable
                                                        default-sort-direction="asc"
                                                        :default-sort="['time', 'asc']"
                                                        checkbox-position="right"
                                                        :header-checkable="false"
                                                        focusable>
                                                    </b-table>
                                                </div>
                                                <div id="desorption-chart-holder">
                                                    <div class="columns" style="margin-left:2px;" id="desorption-chart"></div>
                                                </div>
                                                <br>
                                            </div>
                                        </b-collapse>
                                    </section>
                                    <!-- End of Desorption collapsable -->
                                </div>
                            </div>
                        </b-collapse>
                    </section>
</div>
                    <!-- End of  Acquisition parameters collapsable -->

                    <!-- Samples datatable collapsable -->
                    <section style="width:100%;">
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
                                        <b-button
                                            type="is-dark"
                                            @click="is_sample_attribute_modal_active=true"
                                            outlined
                                            inverted
                                            size="is-small">
                                            Sample attributes
                                        </b-button>
                                        <div><br></div>
                                        <b-table 
                                            id="samples-datatable"
                                            :columns="sample_table_cols"
                                            :data="sample_table_rows"
                                            :checkable="acquisition_status=='not_running' ? true : false"
                                            :header-checkable="false"
                                            :checked-rows.sync="sample_table_checked_rows">
                                        </b-table>
                                        <div><br></div>
                                        <b-button
                                            type="is-dark"
                                            @click="LaunchSampleImport()"
                                            size="is-small"
                                            outlined
                                            inverted>
                                            Import sample
                                        </b-button>
                                        <b-button
                                            type="is-dark"
                                            @click="is_import_h5_modal_active=true"
                                            size="is-small"
                                            outlined
                                            inverted
                                            :disabled="(h5_streamer_status=='ready' && 
                                                        acquisition_status=='not_running') ? false : true">
                                            Import h5 file
                                        </b-button>
                                    </div>
                                </div>
                            </div>
                        </b-collapse>
                    </section>
                    <!-- End of Sample datatable collapable -->

<!-- <div hidden> -->
                    <!-- Targetlist datatable collapable -->
                    <section style="width:100%;">
                        <b-collapse class="card" animation="slide" aria-id="contentIdForA11y3">
                            <div
                                slot="trigger" 
                                slot-scope="props"
                                class="card-header"
                                role="button"
                                aria-controls="contentIdForA11y3">
                                <p class="card-header-title">
                                    Targets
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
                                        <b-button
                                            type="is-dark"
                                            @click="is_excel_clipboard_modal_active=true"
                                            outlined
                                            inverted
                                            size="is-small">
                                            Import targets
                                        </b-button>
                                        <div><br></div>
                                        <b-table 
                                            id="targets-datatable"
                                            :columns="target_table_cols"
                                            :data="target_table_rows" 
                                            :sticky-header="true"
                                            :selected.sync="target_table_selected_row" 
                                            focusable
                                            sortable>
                                        </b-table>
                                    </div>
                                </div>
                            </div>
                        </b-collapse>
                    </section>
<!-- </div> -->
                    <!-- End of TargetList datatable collapable -->
                </div>
                <!-- End of left column -->

                <!-- Right side content -->
                <div class="column is-three-quarters">
                    <SampleView></SampleView>
                </div>
                <!-- End of Right side content -->
            </div>
        </section>
        <!-- End of Main content -->
    </div>
</template>