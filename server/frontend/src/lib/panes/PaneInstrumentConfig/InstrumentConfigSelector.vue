<script setup>
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'

const instrumentConfig = defineModel()
</script>

<template>
  <div class="input-group row" v-if="instrumentConfig.input?.ready">
    <FloatLabel v-if="instrumentConfig.input.creating">
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
      style="width: 70px"
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
