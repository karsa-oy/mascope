import { describe, it, expect } from 'vitest'

import { useColsValidation, useRowsValidation } from '@/lib/dialogs/DialogBatchImport/validation'

const col = (label) => ({ label })

const item = (overrides = {}) => ({
  sample_item_name: 'Sample 1',
  sample_item_type: 'SAMPLE',
  filename: 'sample_POS_001.h5',
  filter_id: null,
  ...overrides
})

const imported = (items = [], overrides = {}) => ({
  type: 'generic',
  items,
  availableIonizationModes: [{ token: 'POS' }, { token: 'NEG' }],
  ...overrides
})

describe('useColsValidation', () => {
  it('passes for fully labeled columns', () => {
    const validation = useColsValidation({ imported: imported() })
    validation.execute({ cols: [col('Sample Name'), col('Sample Type'), col('Filter ID')] })
    expect(validation.passed).toBe(true)
    expect(validation.issues).toHaveLength(0)
  })

  it('fails on unlabeled and duplicated columns', () => {
    const validation = useColsValidation({ imported: imported() })
    validation.execute({ cols: [col('Name'), col(''), col('Name')] })
    expect(validation.passed).toBe(false)
    expect(validation.issues.join(' ')).toContain('All columns should be labeled')
    expect(validation.issues.join(' ')).toContain('duplicated')
  })

  it('requires labels on attribute columns past the third', () => {
    const validation = useColsValidation({ imported: imported() })
    validation.execute({
      cols: [col('Name'), col('Type'), col('Filter'), col(''), col('')]
    })
    expect(validation.passed).toBe(false)
    expect(validation.issues.join(' ')).toContain('Columns 4, 5')
  })

  it('skips column validation for autosampler imports', () => {
    const validation = useColsValidation({ imported: imported([], { type: 'autosampler' }) })
    validation.execute({ cols: [col('')] })
    expect(validation.passed).toBe(true)
  })
})

describe('useRowsValidation', () => {
  it('passes for a consistent import', () => {
    const items = [item()]
    const validation = useRowsValidation({ imported: imported(items) })
    validation.execute({ files: ['sample_POS_001.h5'] })
    expect(validation.passed).toBe(true)
    expect(validation.issues).toHaveLength(0)
  })

  it('flags a sample/file count mismatch', () => {
    const validation = useRowsValidation({ imported: imported([item()]) })
    validation.execute({ files: [] })
    expect(validation.passed).toBe(false)
    expect(validation.issues[0].failures[0]).toContain("doesn't line up")
  })

  it('flags a missing ionization mode token in the filename', () => {
    const items = [item({ filename: 'sample_001.h5' })]
    const validation = useRowsValidation({ imported: imported(items) })
    validation.execute({ files: ['sample_001.h5'] })
    expect(validation.passed).toBe(false)
    expect(validation.issues[0].failures.join(' ')).toContain('Ionization mode token not found')
  })

  it('flags an unknown sample type', () => {
    const items = [item({ sample_item_type: 'NOT_A_TYPE' })]
    const validation = useRowsValidation({ imported: imported(items) })
    validation.execute({ files: ['sample_POS_001.h5'] })
    expect(validation.passed).toBe(false)
  })

  it('enforces filter ID presence rules per sample type', () => {
    const missingRequired = [item({ sample_item_type: 'FILTER_REGENERATION' })]
    let validation = useRowsValidation({ imported: imported(missingRequired) })
    validation.execute({ files: ['sample_POS_001.h5'] })
    expect(validation.issues[0].failures.join(' ')).toContain('must be provided')

    const notAllowed = [item({ sample_item_type: 'INSTRUMENT_BACKGROUND', filter_id: 'ABC123' })]
    validation = useRowsValidation({ imported: imported(notAllowed) })
    validation.execute({ files: ['sample_POS_001.h5'] })
    expect(validation.issues[0].failures.join(' ')).toContain('should not be provided')
  })

  it('validates the filter ID format', () => {
    const items = [item({ sample_item_type: 'FILTER_BACKGROUND', filter_id: 'nope' })]
    const validation = useRowsValidation({ imported: imported(items) })
    validation.execute({ files: ['sample_POS_001.h5'] })
    expect(validation.passed).toBe(false)
    // The validator also pushes a plain-string recommendation into issues,
    // so locate the per-sample failure entry rather than relying on order.
    const failure = validation.issues.find((issue) => issue.failures)
    expect(failure.failures.join(' ')).toContain('incorrectly formatted')
  })
})
