<script setup>
  import { ref, watch, computed, nextTick } from 'vue';

  import table from '@/lib/table'
  import { useKeyStore } from '@/stores'

  const props = defineProps({
    label: {
      type: String,
      required: true,
    },
    cols: {
      type: Array,
      required: true,
    },
    colsFromHeader: {
      type: Boolean,
      required: false,
      default: false,
    },
    info: {
      type: String,
      required: false,
      default: 'Paste spreadsheet cells here',
    },
  })

  const emit = defineEmits(['colsPasted', 'rowsPasted'])

  const rows = ref([])

  const fields = computed(() => props.cols.map((col) => col.field))

  const { control, v } = useKeyStore()


  // WARN possible regrsssion for cols when using colsFromHeader
  async function parseClipboard() {
    if (!(control && v)) return
    navigator.permissions.query({ name: 'clipboard-read' })
    let clipboardText = await navigator.clipboard.readText()
    if (props.colsFromHeader) {
      let headers = table.readHeader(clipboardText)
      let cols = headers.map((header) => ({
        field: header.toLowerCase().replace(/ /g, '_').trim(),
        label: header,
      }))
      emit('colsPasted', cols)
      await nextTick()
    }
    rows.value = table.fromSpreadsheet(
      clipboardText,
      fields.value,
      props.colsFromHeader
    )
    emit('rowsPasted', rows.value)
  }

  watch(control, parseClipboard)
  watch(v, parseClipboard)
</script>

<template>
  <b-field :label="label">
    <template v-if="cols.length > 1 && rows.length > 0">
      <section>
        <section style="font-style: italic; color: #b7b7b7; padding-bottom: 0.5em">
          Paste spreadsheet data again to replace data.
        </section>
        <section>
          <b-table :columns="cols" :data="rows" style="padding-bottom: 0.5em"> </b-table>
        </section>
      </section>
    </template>
    <b-message v-else type="is-info" has-icon>{{ info }}</b-message>
  </b-field>
</template>
