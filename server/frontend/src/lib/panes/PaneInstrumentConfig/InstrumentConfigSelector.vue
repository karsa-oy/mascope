<script setup>
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'

const instrumentConfig = defineModel()
</script>

<template>
  <div class="input-group row" v-if="instrumentConfig.input?.ready">
    <FloatLabel v-if="instrumentConfig.input.creating" class="config-input">
      <InputText
        id="pending-instrument-config"
        v-model="instrumentConfig.input.new.method_file"
        required
      />
      <label for="pending-instrument-config"> Instrument config </label>
    </FloatLabel>
    <FloatLabel v-else class="config-select">
      <Select
        inputId="select-instrument-config"
        v-model="instrumentConfig.input.selected"
        :options="instrumentConfig.input.options"
        :invalid="instrumentConfig.status?.invalid"
        optionLabel="method_file"
      />
      <label for="select-instrument-config"> Instrument config </label>
    </FloatLabel>
    <SelectButton
      v-model="instrumentConfig.input.creating"
      :options="[
        {
          tooltip: 'Use existing',
          label: 'Pick',
          disabled: !instrumentConfig.status?.selectable,
          value: false,
          icon: 'pi pi-search'
        },
        {
          tooltip: 'Create new',
          label: 'Create',
          disabled: false,
          value: true,
          icon: 'pi pi-plus'
        }
      ]"
      optionLabel="tooltip"
      optionValue="value"
      optionDisabled="disabled"
      dataKey="value"
      :allowEmpty="false"
      style="width: 70px; flex-shrink: 0"
    >
      <template #option="{ option }">
        <div
          :id="option.id"
          style="z-index: 100"
          :class="option.icon"
          v-tooltip.bottom="option.tooltip"
        />
      </template>
    </SelectButton>
  </div>
</template>

<style scoped>
.input-group.row {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.config-select,
.config-input {
  flex: 1;
  min-width: 0;
  max-width: 100%;
}

.config-select :deep(.p-select),
.config-input :deep(.p-inputtext) {
  width: 100%;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.config-select :deep(.p-select .p-select-label),
.config-input :deep(.p-inputtext) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
