import { defineModule } from './lib/module'

import { api } from '@/api'

export const useTemplate = defineModule({
  name: 'template',
  key: 'attribute_template_id',
  load: async () =>
    (
      await api.request.read({
        method: 'getAllAttributeTemplates'
      })
    )?.data,
  create: async (template) => {
    return await api.request.create({
      method: 'createAttributeTemplate',
      body: template
    })
  },
  update: async (template) =>
    await api.request.update({
      method: 'updateAttributeTemplate',
      body: { templateId: template.attribute_template_id, body: template }
    }),
  delete: async ({ attribute_template_id, name }) =>
    await api.request.delete({
      method: 'deleteAttributeTemplate',
      body: { templateId: attribute_template_id, templateName: name }
    })
})
