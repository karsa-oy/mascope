<template>
    <div>
        <!-- Modals -->
        <!-- End of modals -->

        <!-- Main content -->
        <div class="box">
            <div style="text-align:right;"
                 v-if="editable">
                <b-button
                    icon-right="settings"
                    type="is-primary"
                    size="is-small"
                    @click="show_edit_functions = !show_edit_functions">
                </b-button>
            </div>
            <h1 style="font-size:16px; text-align:center;">
                <p><b>{{ form_title }}</b>
                </p>
            </h1>
            <div><br></div>
            <div
                v-for="item in form_fields" :key="item.label">
                <template>
                        <b-field :label="item.label">
                            <b-input
                                v-model="item.value"
                                :placeholder="show_edit_functions ? 'default value' : ''"
                                :required="fillable && item.required"
                                :disabled="!fillable"
                                lazy
                                expanded>
                            </b-input>
                            <div v-if="show_edit_functions">
                                <b-button
                                    :id="item.label"
                                    :disabled="item.required"
                                    @click="removeField($event)"
                                    type="is-danger"
                                    icon-right="delete">
                                </b-button>
                            </div>
                        </b-field>
                        <!-- <div><br></div> -->
                </template>
            </div>
            <div v-if="show_edit_functions">
                <b-field label="New field">
                    <b-button
                        @click="addField()"
                        expanded>
                        <b>+</b>
                    </b-button>
                </b-field>
            </div>
            <div><br></div>
            <b-field label="Reuse template" v-if="Boolean(template_path)">
                <div class="columns">
                    <div class="column is-half" style="text-align:center">
                        <b-select
                            v-model="loaded_template"
                            placeholder="Load template"
                            expanded>
                            <option
                                v-for="t in available_templates"
                                :value="t"
                                :key="t.name">
                                {{ t.name }}
                            </option>
                        </b-select>
                    </div>
                    <div
                        class="column is-one-seventh"
                        style="text-align:left"
                        v-if="show_edit_functions">
                        <b-button
                            :disabled="!loaded_template || loaded_template.name=='default template'"
                            @click="deleteTemplate()"
                            type="is-danger"
                            icon-right="delete">
                        </b-button>
                    </div>
                    <div
                        class="column is-one-third"
                        style="text-align:center"
                        v-if="show_edit_functions">
                        <b-button
                            @click="saveTemplate()"
                            :disabled="!form_fields.length"
                            expanded>
                            Save template
                        </b-button>
                    </div>
                </div>
            </b-field>
        </div>
        <!-- End of main content -->
    </div>
</template>
    
<script type="text/javascript">

import { makeValidFilename, shallow_copy } from "../karsalib.js"

var fs = require('fs');
var path = require('path');
var _ = require('underscore');


export default {
    name: "MetaDataForm",

    props: {
        default_template: {
            type: Array,
            required: false,
            default: function () { return [] },
            },
        editable: {
            type: Boolean,
            required: false,
            default: false,
            },
        fillable: {
            type: Boolean,
            required: false,
            default: true,
            },
        form_title: {
            type: String,
            required: false,
            default: "",
            },
        initial_template: {
            type: Array,
            required: false,
            default: null,
            },
        template_path: {
            type: String,
            required: false,
            default: null,
            },
    },

    data() {
        return {
            always_available_templates: [
                {
                    'name': "default template",
                    'template': this.default_template
                },
            ],
            available_templates: this.always_available_templates,
            form_fields: [],
            loaded_template: null,
            show_edit_functions: true,
        }
    },
    created() {
        if (this.template_path) {
            this.findTemplates();
        }
        if (this.initial_template) {
            this.loaded_template = {'name': null,
                                    'template': this.initial_template
                                    };
        } else {
            this.loaded_template = {'name': "default template",
                                    'template': this.default_template
                                    };
        }
    },
    mounted() {
        this.$nextTick(() => {
            // When creating the form, show_edit_functions is true to render space
            // for the buttons etc, now set it to false by default
            this.show_edit_functions = false;
        });        
    },
    methods: {
        addField() {
            this.$buefy.dialog.prompt({
                message: "Add field to template",
                confirmText: 'Add',
                inputAttrs: {
                    placeholder: 'field label',
                    maxlength: 100,
                },
                trapFocus: true,
                onConfirm: (field_to_add) => {
                    this.form_fields.push({'label': field_to_add,
                                           'value': ""
                                           });
                    this.loaded_template = null;
                }
            })
            
        },
        deleteTemplate() {
            this.$buefy.dialog.confirm({
                    title: 'Deleting template',
                    message: 'Are you sure you want to delete template <b>' + this.loaded_template.name + "</b>?",
                    confirmText: 'Delete',
                    onConfirm: () => {
                        fs.unlinkSync(this.loaded_template.path);
                        this.loaded_template = null;
                        this.findTemplates();
                        }
                })
        },
        findTemplates() {
            var self = this;
            self.available_templates = shallow_copy(this.always_available_templates);
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
                            template.path = file_path;
                            self.available_templates.push(template);
                        }
                    }
                });
            });
        },
        removeField(event) {
            // Field to remove label is in button element id, find it from the event data
            let field_to_remove = "";
            for (let i in event.path) {
                field_to_remove = event.path[i].id;
                if (field_to_remove)
                    break;
            }
            if (!field_to_remove) {
                // Failed to find the button id
                console.log("field_to_remove not found at event.path[1].id: ", event);
                return
            }
            for (let i=0; i < this.form_fields.length; ++i) {
                if (_.isEqual(field_to_remove, this.form_fields[i].label)) {
                    this.form_fields.splice(i, 1);
                    break;
                }
            }
            this.loaded_template = null;
        },
        saveTemplate() {
            this.$buefy.dialog.prompt({
                message: "Template name",
                confirmText: 'Save',
                inputAttrs: {
                    placeholder: 'template name',
                    maxlength: 100,
                },
                trapFocus: true,
                onConfirm: (template_name) => this.writeTemplate(template_name)
            })
        },
        writeTemplate(template_name) {
            let filename = makeValidFilename(template_name) + ".json";
            let template_path = path.join(this.template_path, filename);
            if (fs.existsSync(template_path)) {
                this.$buefy.dialog.alert({
                    title: 'Failed to save template',
                    message: 'Template with given name exists already. Please choose a different name',
                    type: 'is-danger',
                })
                return
            }
            let template_data = {
                        name: template_name,
                        template: this.form_fields
                        }
            let template_json = JSON.stringify(template_data, null, 4);
            fs.writeFileSync(template_path, template_json);
            // Add to list of available templates
            this.available_templates.push(template_data);
            // Set as loaded
            this.loaded_template = template_data;
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
                this.form_fields = shallow_copy(new_value.template);
            }
        },
    },
}

</script>