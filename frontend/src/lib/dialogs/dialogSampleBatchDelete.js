import { useConfirm } from 'primevue/useconfirm'

import { useBatchStore } from '@/stores'

export function useSampleBatchDeleteDialog() {
  const batchStore = useBatchStore()
  const confirm = useConfirm()

  return (batch) =>
    confirm.require({
      message: `Are you sure you want to delete the batch '${batch.sample_batch_name}'?`,
      header: `Delete sample batch '${batch.sample_batch_name}'`,
      icon: 'pi pi-exclamation-triangle',
      rejectProps: {
        label: 'Cancel',
        severity: 'secondary'
      },
      acceptProps: {
        icon: 'pi pi-trash',
        label: 'Delete',
        severity: 'danger'
      },
      accept: () => {
        batchStore.deleteBatch(batch)
      }
    })
}
