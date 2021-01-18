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
                            <button class="button" type="button" is-dark @click="edit_row_in_config_desorption_table()">Save</button>
                            <button class="button" type="button" is-dark @click="is_edit_temperature_ramp_modal_active=false">Close</button>
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
                                    :min-datetime="import_min_datetime"
                                    :max-datetime="import_max_datetime">
                                </b-datetimepicker>
                            </b-field>
                            <b-field label="End">
                                <b-datetimepicker
                                    v-model="import_end_time"
                                    placeholder="End datetime"
                                    :min-datetime="import_start_time"
                                    :max-datetime="import_max_datetime">
                                </b-datetimepicker>
                            </b-field>
                            <button
                                class="button"
                                type="button"
                                @click="FetchH5s()"
                                is-dark
                                :disabled="(h5_streamer_status=='ready' &&
                                            import_start_time != null &&
                                            import_end_time != null
                                            ) ? false : true">
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
                                :disabled="!import_h5_table_checked_rows.length">
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
                            <b-field label="Start">
                                <b-datetimepicker
                                    v-model="import_start_time"
                                    placeholder="Start datetime"
                                    :min-datetime="import_min_datetime"
                                    :max-datetime="import_max_datetime">
                                </b-datetimepicker>
                            </b-field>
                            <b-field label="End">
                                <b-datetimepicker
                                    v-model="import_end_time"
                                    placeholder="End datetime"
                                    :min-datetime="import_start_time"
                                    :max-datetime="import_max_datetime">
                                </b-datetimepicker>
                            </b-field>
                            <button
                                class="button"
                                type="button"
                                @click="FetchSamples()"
                                is-dark>
                                Fetch sample list
                            </button>
                            <div><br></div>
                            <b-table 
                                id="h5-samples-table"
                                :columns="import_sample_table_cols"
                                :data="import_sample_table_rows"
                                :checkable="true"
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
            </b-modal>
        </section>
        <!-- End of sample import modal -->
        <!-- All modals should not be after this -->

        <section class="loading">
            <!-- Placeholder for loading div -->
        </section>

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
                        type="is-success"
                        size="is-large">
                    </b-progress>
                    <!-- <div hidden> -->
                    <div class="acquisition-parameters" style="margin-bottom:0.4rem;padding:10px;">
                        <b-field>
                            <b-button
                                v-bind:icon-left="acquisition_status=='starting' || 
                                                  acquisition_status=='stopping' ||
                                                  instrument_status=='not_ready' ? 'flattr' : ''"
                                :type="acquisition_button_type"
                                :disabled="acquisition_mode=='triggered' || instrument_status=='not_ready'"
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
                                                        <b-input size="is-small" v-model="time" type="number" placeholder="time"></b-input>
                                                    </div>
                                                    <div class="column" style="width:30%">
                                                        <b-input size="is-small" v-model="temperature" type="number" placeholder="temperature"></b-input>
                                                    </div>
                                                    <div class="" style="width:40%; padding-top:15px;">
                                                        <b-button type="is-dark" size="is-small" @click="save_new_row_in_config_desorption_table()" outlined inverted >Save</b-button>
                                                        &nbsp; 
                                                        <b-button type="is-dark" size="is-small" @click="show_add_new_row=false; time=''; temperature='';" outlined inverted>Cancel</b-button>
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
                                    <div class="collected-sample-attributes">
                                        <b-button
                                            type="is-dark"
                                            @click="is_sample_attribute_modal_active=true"
                                            outlined
                                            inverted>
                                            Sample attributes
                                        </b-button>
                                        <div><br></div>
                                        <b-table 
                                            id="samples-datatable"
                                            :columns="sample_table_cols"
                                            :data="sample_table_rows"
                                            :checkable="acquisition_status=='not_running' ? true : false"
                                            :checked-rows.sync="sample_table_checked_rows">
                                        </b-table>
                                        <div><br></div>
                                        <b-button
                                            type="is-dark"
                                            @click="is_import_sample_modal_active=true"
                                            outlined
                                            inverted>
                                            Import sample
                                        </b-button>
                                        <div><br></div>
                                        <b-button
                                            type="is-dark"
                                            @click="is_import_h5_modal_active=true"
                                            outlined
                                            inverted
                                            :disabled="acquisition_status=='not_running' ? false : true">
                                            Import h5 file
                                        </b-button>
                                    </div>
                                </div>
                            </div>
                        </b-collapse>
                    </section>
                    <!-- End of Sample datatable collapable -->

<div hidden>
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
                                    <div class="collected-sample-attributes">
                                        <div class="samples-columns-selector">
                                            <b-dropdown
                                                aria-role="list"
                                                type="is-dark"
                                                position="is-top-right"
                                                multiple>
                                                <b-button
                                                    icon-left="menu"
                                                    size="is-small"
                                                    slot="trigger"
                                                    class="tag is-dark"
                                                    outlined
                                                    inverted>
                                                    Columns visibility
                                                </b-button>
                                                
                                                <div
                                                    v-for="(row, index) in target_table_data[0]"
                                                    :key="index">
                                                    <div id="filter-checkboxes">
                                                        <input
                                                            type="checkbox"
                                                            id="filter-checkbox-input"
                                                            :value="index"
                                                            :checked="true"
                                                            v-model="target_table_filter_rows">
                                                        <label for="index">
                                                            {{ index }}
                                                        </label>
                                                    </div>
                                                </div>
                                            </b-dropdown>
                                        </div>
                                        <div class="targetlist-datatable">
                                            <b-table 
                                                id="targets-datatable"
                                                :data="target_table_data" 
                                                type="is-white" 
                                                :narrowed="true" 
                                                :bordered="true" 
                                                :paginated="true" 
                                                :per-page="5" 
                                                :pagination-simple="false" 
                                                sort-icon="arrow-up"
                                                default-sort-direction="asc"
                                                :checked-rows.sync="selected_target_table_rows" 
                                                :header-checkable="false"
                                                :checkable="acquisition_status=='not_running' ? true:false"
                                                focusable
                                                sortable
                                                :columns="target_table_columns"
                                                >
                                                <template slot-scope="props">
                                                    <b-table-column field="target" :visible="target_table_filter_rows.includes('target') ? true : false" id="target" label="Target" width="40" sortable>
                                                        {{ props.row.target }}
                                                    </b-table-column>
                                                    <b-table-column field="composition" :visible="target_table_filter_rows.includes('composition') ? true : false" id="composition" label="Composition" width="40" sortable>
                                                        {{ props.row.composition }}
                                                    </b-table-column>            
                                                    <b-table-column field="signal" :visible="target_table_filter_rows.includes('signal') ? true : false" id="signal" label="Signal" width="40" sortable>
                                                        {{ props.row.signal }}
                                                    </b-table-column> 
                                                    <b-table-column field="mz_error" :visible="target_table_filter_rows.includes('mz_error') ? true : false" id="mz_error" label="m/z err." width="40" sortable>
                                                        {{ props.row.mz_error }}
                                                    </b-table-column>
                                                    <b-table-column field="abu_score" :visible="target_table_filter_rows.includes('abu_score') ? true : false" id="abu_score" label="Iso.ratio" width="40" sortable>
                                                        {{ props.row.abu_score }}
                                                    </b-table-column> 
                                                    <b-table-column field="iso_r2" :visible="target_table_filter_rows.includes('iso_r2') ? true : false" id="iso_r2" label="Iso.R2" width="40" sortable>
                                                        {{ props.row.iso_r2 }}
                                                    </b-table-column>                                            
                                                    <b-table-column field="snos" :visible="target_table_filter_rows.includes('snos') ? true : false" id="snos" label="Sample numbers" width="40" sortable>
                                                        {{ props.row.snos }}
                                                    </b-table-column>
                                                    <b-table-column field="mass" :visible="target_table_filter_rows.includes('mass') ? true : false" id="mass" label="m/z" width="40" sortable>
                                                        {{ props.row.mass }}
                                                    </b-table-column>
                                                </template>
                                            </b-table>
                                        </div>
                                    </div>
                                    <div class="target-list-parameters-sliders">
                                        <!--Inner Colapsable for browse button -->
                                        <section style="width:100%;padding:0.5rem;">
                                            <b-collapse class="inner-collapsable card" :open="false" animation="slide" aria-id="contentIdForA11y3">
                                                <div
                                                    slot="trigger" 
                                                    slot-scope="props"
                                                    class="inner-collapsable card-header"
                                                    role="button"
                                                    aria-controls="contentIdForA11y3">
                                                    <p class="card-header-title">
                                                        Detection Parameters
                                                    </p>
                                                    <a class="card-header-icon">
                                                    <b-icon
                                                        :icon="props.open ? 'menu-down' : 'menu-up'">
                                                    </b-icon>
                                                    </a>
                                                </div>
                                                <div class="card-content">
                                                    <div class="content inner-collapsable-content" >
                                                        <div class="field filter-toggle-field">
                                                            <div class="filter-toggle-group">
                                                                <p>
                                                                    Apply filter:
                                                                    <b-switch v-model="apply_filters"
                                                                        true-value="Yes"
                                                                        false-value="No">
                                                                        {{ apply_filters }}
                                                                    </b-switch>  
                                                                 </p>                                                             
                                                            </div>
                                                        </div>

                                                        <div class="spacer">
                                                            <div v-if="apply_filters" id="filters_parameters">
                                                                <div class="is-full">
                                                                    <b-field label="threshold (mV/ext)">
                                                                        <b-slider type="is-white" inverted outlined @change="update_slider_values_and_process_data" size="is-small" :step="0.1" :min="-5" :max="1" v-model="threshold_value" ticks>
                                                                            <template v-for="(val, ind) in ([-5, -4, -3, -2, -1, 1, 0, 1 ])">
                                                                                <b-slider-tick v-bind:key="'thresh_'+ind" v-bind:value="val">{{ val }}</b-slider-tick>
                                                                            </template>
                                                                        </b-slider>
                                                                    </b-field>
                                                                    <b-field label="m/z error tolerance (ppm)">
                                                                        <b-slider type="is-white" @change="update_slider_values_and_process_data" size="is-small" :step="1" :min="0" :max="20" v-model="mz_value" ticks>
                                                                            <template v-for="(val, ind) in (0,20)">
                                                                                <b-slider-tick v-bind:key="'mz_'+ind" :value="val">{{ val }}</b-slider-tick>
                                                                            </template>
                                                                        </b-slider>
                                                                    </b-field>
                                                                    <b-field label="isotope ratio error tolerance (%)">
                                                                        <b-slider type="is-white" @change="update_slider_values_and_process_data" size="is-small" :step="0.01" :min="0.0" :max="1.0" v-model="iso_err_tol_value" ticks>
                                                                            <template v-for="(val, ind) in [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.0]">
                                                                                <b-slider-tick v-bind:key="'iso_err_'+ind" :value="val">{{ val*100 }}</b-slider-tick>
                                                                            </template>
                                                                        </b-slider>
                                                                    </b-field>
                                                                    <b-field label="isotope correlation error tolerance (%)">
                                                                        <b-slider type="is-white" @dragend="update_slider_values_and_process_data" size="is-small" :step="0.01" :min="0.0" :max="1.0" v-model="iso_corr_err_value">
                                                                            <template v-for="(val, ind) in  [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.0]">
                                                                                <b-slider-tick v-bind:key="'iso_corr_'+ind" :value="val">{{ val * 100 }}</b-slider-tick>
                                                                            </template>
                                                                        </b-slider>
                                                                    </b-field>
                                                                </div>
                                                                <div class="column is-full">
                                                                    <b-field id="update-peaklist-db" v-if="enable_save_new_slider_values">
                                                                        <b-button @click="save_peaklist_new_values_in_db" type="is-primary" inverted outlined>Save new values</b-button>
                                                                    </b-field>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </b-collapse>
                                        </section>
                                        <!--Inner Collapsable for browse button end -->
                                    </div>
                                </div>
                            </div>
                        </b-collapse>
                    </section>
</div>
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