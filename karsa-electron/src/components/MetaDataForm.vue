<template>
    <div>
        <!-- Modals -->
        <!--- Add field modal-->
        <section class="add-field-modal">
            <b-modal :active.sync="is_modal_add_field_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px">
                    <!-- Main content -->
                    <div>
                        <section class="modal-card-body">
                            <b-field label="Field to add">
                                <b-input
                                    v-model="field_to_add"
                                    required
                                    expanded>
                                </b-input>
                            </b-field>
                        </section>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button
                            type="is-primary"
                            @click="addField()"
                            :disabled="!field_to_add.length">
                            Add
                        </b-button>
                        <b-button
                            @click="is_modal_add_field_active=false">
                            Cancel
                        </b-button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of remove field modal-->         <!--- Remove field modal-->
        <section class="remove-field-modal">
            <b-modal :active.sync="is_modal_remove_field_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px">
                    <!-- Main content -->
                    <div>
                        <section class="modal-card-body">
                            <b-field label="Field to remove">
                                <b-select
                                    v-model="field_to_remove"
                                    required
                                    expanded>
                                    <option
                                        v-for="f in form_fields"
                                        :value="f.label"
                                        :key="f.label">
                                        {{ f.label }}
                                    </option>
                                </b-select>
                            </b-field>
                        </section>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button
                            type="is-primary"
                            @click="removeField()"
                            :disabled="!field_to_remove.length">
                            Remove
                        </b-button>
                        <b-button
                            @click="is_modal_remove_field_active=false">
                            Cancel
                        </b-button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of remove field modal--> 
        <!-- End of modals -->

        <!-- Main content -->
        <div v-for="item in form_fields" :key="item.label">
            <template>
                <b-field :label="item.label">
                    <b-input
                        v-model="item.value"
                        lazy>
                    </b-input>
                </b-field>
            </template>
        </div>
        <div><br></div>
        <section v-if="Boolean(template_path)">
            <div class="columns">
                <div class="column is-half" style="text-align:center">
                    <div class="rows">
                        <div class="row">
                            <b-button
                                @click="is_modal_add_field_active=true"
                                is-dark>
                                New field
                            </b-button>
                        </div>
                        <div class="row">
                            <b-button
                                @click="is_modal_remove_field_active=true"
                                :disabled="!form_fields.length"
                                is-dark>
                                Remove field
                            </b-button>
                        </div>
                    </div>
                </div>
                <div class="column is-half" style="text-align:center">
                    <div class="rows">
                        <div class="row">
                            <b-select
                                v-model="loaded_template"
                                placeholder="Load template"
                                is-dark>
                                <option
                                    v-for="t in available_templates"
                                    :value="t.template"
                                    :key="t.name">
                                    {{ t.name }}
                                </option>
                            </b-select>
                        </div>
                        <div class="row">
                            <b-button
                                @click="saveTemplate()"
                                :disabled="!form_fields.length"
                                is-dark>
                                Save template
                            </b-button>
                        </div>
                    </div>
                </div>
            </div>
        </section>
        <!-- End of main content -->
    </div>
</template>
    
<script type="text/javascript">

import { shallow_copy } from "../karsalib.js"

var fs = require('fs');
var path = require('path');
var _ = require('underscore');


export default {
    name: "MetaDataForm",

    props: {
        default_template: Array,
        template_path: String,
    },

    data() {
        return {
            available_templates: [
                {
                    'name': "default",
                    'template': this.default_template || []
                },
                {
                    'name': "empty",
                    'template': {}
                },
            ],
            field_to_add: "",
            field_to_remove: "",
            form_fields: [],
            form_title: "MetaDataForm",
            loaded_template: null,

            is_modal_add_field_active: false,
            is_modal_remove_field_active: false,
        }
    },
    created() {
        if (this.template_path) {
            this.findTemplates();
        }
        this.form_fields = this.default_template;
    },
    methods: {
        addField() {
            this.form_fields.push({'label': this.field_to_add,
                                   'value': ""
                                   });
            this.is_modal_add_field_active = false;
            this.field_to_add = "";
            this.loaded_template = null;
        },
        convertToValidFilename(string) {
            return (string.replace(/[/|\\:*?"<>]/g, "_"));
        },
        removeField() {
            for (let i=0; i < this.form_fields.length; ++i) {
                if (_.isEqual(this.field_to_remove, this.form_fields[i].label)) {
                    this.form_fields.splice(i, 1);
                    break;
                }
            }
            this.is_modal_remove_field_active = false;
            this.loaded_template = null;
        },
        findTemplates() {
            var self = this;
            // Read templates from disk
            fs.readdir(this.template_path, function (err, files) {
                if (err) {
                    throw new Error(err);
                }
                files.forEach(function (file) {
                    var file_path = path.join(self.template_path, file);
                    var stat = fs.statSync(file_path);
                    if (stat.isFile()) {
                        // Found a file
                        let file_ext = path.parse(file).ext;
                        if (_.isEqual(file_ext, '.json')) {
                            // console.log("file: ", file_path, stat);
                            let template = JSON.parse(fs.readFileSync(file_path, 'utf8'));
                            self.available_templates.push(template);
                        }
                    }
                });
            });
        },
        saveTemplate() {
            this.$buefy.dialog.prompt({
                message: "Template name",
                inputAttrs: {
                    placeholder: 'template name',
                    maxlength: 100
                },
                trapFocus: true,
                onConfirm: (template_name) => this.writeTemplate(template_name)
            })
        },
        writeTemplate(template_name) {
            let template_data = {
                        name: template_name,
                        template: this.form_fields
                        }
            let template_json = JSON.stringify(template_data, null, 4);
            let filename = this.convertToValidFilename(template_name) + ".json";
            let template_path = path.join("templates", filename);
            fs.writeFileSync(template_path, template_json);
            // Add to list of available templates
            this.available_templates.push(template_data);
        }
    },
    watch: {
        form_fields: {
            handler(new_value) {
                this.$emit("metaDataUpdated", new_value);
            },
            deep: true
        },
        loaded_template: function(new_value) {
            if (new_value) {
                // Make a copy to avoid mutating the loaded template directly
                this.form_fields = shallow_copy(new_value);
            }
        },
    },
}

</script>