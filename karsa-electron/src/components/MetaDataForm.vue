<template>
    <div>
        <!-- Modals -->
        <!--- Remove field modal-->
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
                        <header class="modal-card-head">
                            <p class="modal-card-title">
                                New project
                            </p>
                        </header>
                        <section class="modal-card-body">
                            <b-field label="Field to remove">
                                <b-select
                                    placeholder="Select a project"
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
                        <button
                            class="button"
                            type="button"
                            @click="removeField()"
                            is-dark>
                            Remove
                        </button>
                        <button
                            class="button"
                            type="button"
                            is-dark
                            @click="is_modal_remove_field_active=false">
                            Cancel
                        </button>
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
                    <b-input v-model="item.value">
                    </b-input>
                </b-field>
            </template>
        </div>
        <div><br></div>
        <b-field>
            <b-button
                @click="addField()"
                is-dark>
                New field
            </b-button>
            <b-button
                @click="is_modal_remove_field_active=true"
                :disabled="!form_fields.length"
                is-dark>
                Remove field
            </b-button>
        </b-field>
        <!-- End of main content -->
    </div>
</template>
    
<script type="text/javascript">

var _ = require('underscore');


export default {
    name: "MetaDataForm",

    data() {
        return {
            field_to_remove: "",
            form_fields: [],
            is_modal_remove_field_active: false,
        }
    },
    created() {

    },
    methods: {
        addField() {
            this.$buefy.dialog.prompt({
                    message: "Field label: ",
                    inputAttrs: {
                        maxlength: 255,
                    },
                    trapFocus: true,
                    onConfirm: (value) => this.form_fields.push(
                                                        {'label': value,
                                                        'value': ""
                                                        })
                })
        },
        removeField() {
            for (let i=0; i < this.form_fields.length; ++i) {
                if (_.isEqual(this.field_to_remove, this.form_fields[i].label)) {
                    this.form_fields.splice(i, 1);
                    break;
                }
            }
            this.is_modal_remove_field_active = false;
        },
    },
    watch: {

    },
}

</script>