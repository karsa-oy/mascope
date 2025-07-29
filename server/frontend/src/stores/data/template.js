import { defineModule } from './lib/module'

import { api } from '@/api'

export const useTemplate = defineModule({
  name: 'template',
  key: 'attribute_template_id',
  load: {
    method: () =>
      api.http.get(`/attribute_templates`, {
        use: 'read',
        type: 'load_attribute_templates'
      })
  },
  create: (template) =>
    api.http.post(`/attribute_templates`, template, {
      use: 'create',
      type: 'create_attribute_template'
    }),
  update: (template) =>
    api.http.patch(`/attribute_templates/${template.attribute_template_id}`, template, {
      use: 'update',
      type: 'update_attribute_template'
    }),
  delete: ({ attribute_template_id }) =>
    api.http.delete(`/attribute_templates/${attribute_template_id}`, {
      use: 'delete',
      type: 'delete_attribute_template'
    })
})
