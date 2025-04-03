import { useConfirm } from 'primevue/useconfirm'

import { useApp } from '@/stores'

export function useBatchDeleteDialog() {
  const app = useApp()
  const confirm = useConfirm()

  return (batch) =>
    confirm.require({
      icon: 'pi pi-exclamation-triangle',
      header: `Delete sample batch '${batch.sample_batch_name}'`,
      message: `Are you sure you want to delete the batch '${batch.sample_batch_name}'?`,
      accept: () => {
        app.data.batch.delete(batch)
      },
      acceptProps: {
        icon: 'pi pi-trash',
        label: 'Delete',
        severity: 'danger'
      },
      rejectProps: {
        label: 'Cancel',
        severity: 'secondary'
      }
    })
}
