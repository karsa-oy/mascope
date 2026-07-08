<script setup>
import { computed } from 'vue'

import Button from 'primevue/button'

import { useApp } from '@/stores'
import { BaseTierTag } from '@/lib/base'
import { num } from '@/lib/formatters'
import { formatIsotopeFormula } from '@/lib/chem'

const app = useApp()

// Toggles the Sample view's bottom pane between the time series (default) and
// the Re-search panel. Owned by the parent (PaneTabSample); the inspector only
// flips it on.
const showSearch = defineModel('showSearch', { type: Boolean, default: false })

// The committed assignment for the focused peak (from the latest run).
const focusedAssignment = computed(() =>
  app.data.peakAssignment.peak.forPeak(app.data.peak.focused?.peak_id)
)

// Arbitration / chemistry provenance: chemical plausibility (Seven Golden
// Rules), arbitration confidence, calibrated P(correct), and a tie flag.
const provenance = computed(() => focusedAssignment.value?.provenance ?? null)

const fitPercent = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0
})
const formatFit = (value) =>
  value != null && !Number.isNaN(value) ? fitPercent.format(value) : '-'

// The isotopologue family (M0 + M+1, M+2 ...) of the focused assignment.
const family = computed(() => app.data.peakAssignment.peak.familyOf(focusedAssignment.value))

// Main isotope (M0) of the family; theoretical abundances are relative to it.
const m0 = computed(
  () => family.value.find((f) => f.role === 'M0' || f.isotope_label === 'M0') ?? null
)

// Compact substitution label (e.g. "[15N]", "[81Br][2H]") from the full
// isotopologue formula; falls back to the M0/M+1 offset label.
const isoLabel = (iso) =>
  iso.isotope_formula ? formatIsotopeFormula(iso.isotope_formula) : iso.isotope_label || '-'

// Theoretical (predicted) relative abundance of an isotopologue as a fraction
// of M0, recovered from the stored errors:
//   theoretical_rel = observed_rel / (1 + abundance_error),  observed_rel = I / I(M0)
const theoreticalRel = (iso) => {
  const base = m0.value?.sample_peak_intensity
  if (!base || base <= 0 || iso.sample_peak_intensity == null) return null
  const observed = iso.sample_peak_intensity / base
  const denom = 1 + (iso.abundance_error ?? 0)
  return denom > 0 ? observed / denom : null
}
const relAbuFmt = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 0,
  maximumFractionDigits: 1
})
const formatRel = (value) => (value != null ? relAbuFmt.format(value) : '-')

// Per-isotopologue match quality; M0 is the reference and never "poor".
const isPoorMatch = (iso) => {
  if (iso.role === 'M0' || iso.isotope_label === 'M0') return false
  const ab = iso.abundance_error != null ? 1 - Math.min(1, Math.abs(iso.abundance_error)) : 1
  const mz = iso.mz_error_ppm != null ? Math.max(0, 1 - 0.01 * Math.abs(iso.mz_error_ppm)) : 1
  return ab * mz < 0.5
}

// Stats for a close alternative (runner-up), surfaced on hover. Database-stage
// runner-ups carry fit + m/z error + plausibility; untargeted runner-ups are
// formula-only (the untargeted search returns competitor names without
// per-candidate fit), so fit reads "not scored" for them.
const altTooltip = (alt) => {
  const lines = [
    `fit: ${alt.fit_score != null ? formatFit(alt.fit_score) : '— not scored (untargeted)'}`
  ]
  if (alt.mz_error_ppm != null) {
    lines.push(`m/z error: ${num.mzError.format(alt.mz_error_ppm)} ppm`)
  }
  lines.push(`plausibility: ${alt.plausibility != null ? formatFit(alt.plausibility) : '—'}`)
  if (alt.source) lines.push(`source: ${alt.source}`)
  return lines.join('\n')
}
</script>

<template>
  <div
    v-if="app.data.peak.list.length > 0"
    class="assign-root col"
    style="gap: 1rem; align-items: stretch; width: 100%"
    v-help.top="{
      message: `
        <h1>Peak Assignment</h1>
        <p>
        The committed assignment for the selected peak: its fitted composition,
        confidence tier, evidence, isotopologue family and close alternatives.
        </p>
        <p>
        Select peaks by clicking rows in the ledger, or the vertical grey peak
        lines in the spectrum chart. Use <b>Re-search</b> to search compositions
        for the peak on demand.
        </p>`
    }"
  >
      <section v-if="focusedAssignment" class="inspector">
        <div class="insp-head">
          <div class="insp-formula">
            {{ focusedAssignment.assigned_formula || 'Unassigned' }}
          </div>
          <BaseTierTag
            :tier="focusedAssignment.tier"
            :fit-score="focusedAssignment.fit_score"
            :role="focusedAssignment.role"
            :source="focusedAssignment.source"
          />
        </div>
        <div
          class="insp-sub"
          v-if="
            focusedAssignment.ion_formula ||
            focusedAssignment.isotope_label ||
            focusedAssignment.source
          "
        >
          <span v-if="focusedAssignment.ion_formula">{{ focusedAssignment.ion_formula }}</span>
          <span v-if="focusedAssignment.isotope_label">
            &middot; {{ focusedAssignment.isotope_label }}</span
          >
          <span v-if="focusedAssignment.source" class="src">
            &middot; {{ focusedAssignment.source }}</span
          >
        </div>
        <div class="evidence">
          <div class="ev">
            <span class="k">fit</span>
            <span class="v">{{ formatFit(focusedAssignment.fit_score) }}</span>
          </div>
          <div class="ev" v-if="focusedAssignment.mz_error_ppm != null">
            <span class="k">m/z error</span>
            <span class="v">{{ num.mzError.format(focusedAssignment.mz_error_ppm) }} ppm</span>
          </div>
          <div class="ev" v-if="focusedAssignment.abundance_error != null">
            <span class="k">abund. error</span>
            <span class="v">{{
              num.relativeAbundanceError.format(focusedAssignment.abundance_error)
            }}</span>
          </div>
          <div class="ev" v-if="focusedAssignment.isotope_label">
            <span class="k">isotope</span>
            <span class="v">{{ focusedAssignment.isotope_label }}</span>
          </div>
          <div class="ev" v-if="provenance?.plausibility != null">
            <span class="k" v-tooltip.top="'Chemical plausibility (Seven Golden Rules)'"
              >plausibility</span
            >
            <span class="v">{{ formatFit(provenance.plausibility) }}</span>
          </div>
          <div class="ev" v-if="provenance?.confidence != null">
            <span
              class="k"
              v-tooltip.top="'Arbitration confidence: winner share of fit x plausibility'"
              >confidence</span
            >
            <span class="v"
              >{{ formatFit(provenance.confidence)
              }}<span
                v-if="provenance.is_tie"
                class="tie-flag"
                v-tooltip.top="'Runner-up too close to call'"
                >&nbsp;tie</span
              ></span
            >
          </div>
          <div class="ev" v-if="provenance && provenance.calibrated !== undefined">
            <span
              class="k"
              v-tooltip.top="'Calibrated probability the assignment is correct'"
              >P(correct)</span
            >
            <span class="v" v-if="provenance.p_correct != null">
              {{ formatFit(provenance.p_correct)
              }}<span
                v-if="provenance.calibration?.provisional"
                class="prov-flag"
                v-tooltip.top="'Provisional calibration curve - directionally right, not hardened'"
                >&nbsp;prov.</span
              ></span
            >
            <span
              class="v uncal"
              v-else
              v-tooltip.top="'No calibration curve for this instrument'"
              >uncalibrated</span
            >
          </div>
        </div>
        <div v-if="family.length > 1" class="isotopologues">
          <div class="alts-label">Isotopologues</div>
          <div class="iso-head">
            <span>iso</span><span>m/z</span><span>ppm</span
            ><span v-tooltip.top="'Theoretical relative abundance (fraction of M0)'">abu.</span>
          </div>
          <div class="iso-rows">
            <div
              v-for="iso in family"
              :key="iso.peak_assignment_id"
              class="iso-row"
              :class="{
                current: iso.sample_peak_id === focusedAssignment.sample_peak_id,
                poor: isPoorMatch(iso)
              }"
              v-tooltip.left="
                isPoorMatch(iso)
                  ? 'Poorly matched isotopologue (abundance / m/z off) - click to focus'
                  : 'Focus this isotopologue peak'
              "
              @click="app.data.peak.focus({ peak_id: iso.sample_peak_id })"
            >
              <span class="iso-label" v-tooltip.left="iso.isotope_formula || iso.isotope_label"
                ><span v-if="isPoorMatch(iso)" class="pi ph ph-warning poor-icon" />{{
                  isoLabel(iso)
                }}</span
              >
              <span class="iso-mz">{{ num.mz.format(iso.sample_peak_mz) }}</span>
              <span class="iso-err">{{
                iso.mz_error_ppm != null ? `${num.mzError.format(iso.mz_error_ppm)}` : '—'
              }}</span>
              <span class="iso-rel">{{ formatRel(theoreticalRel(iso)) }}</span>
            </div>
          </div>
        </div>
        <div v-if="focusedAssignment.alternatives?.length" class="alts">
          <div class="alts-label">
            Close alternatives
            <span class="alts-count">{{ focusedAssignment.alternatives.length }}</span>
          </div>
          <div class="alts-list">
            <div
              v-for="(alt, i) in focusedAssignment.alternatives"
              :key="i"
              class="alt"
              v-tooltip.left="altTooltip(alt)"
            >
              <span class="f">{{ alt.assigned_formula || alt.ion_formula || '?' }}</span>
              <span class="s">
                <span v-if="alt.fit_score != null"
                  >fit {{ formatFit(alt.fit_score)
                  }}<span v-if="alt.mz_error_ppm != null">
                    &middot; {{ num.mzError.format(alt.mz_error_ppm) }} ppm</span
                  ></span
                >
                <span v-else-if="alt.plausibility != null">plaus {{ formatFit(alt.plausibility) }}</span>
                <span v-else class="no-stats"><span class="pi ph ph-info" /></span>
              </span>
            </div>
          </div>
        </div>
        <div class="insp-actions">
          <Button
            :label="showSearch ? 'Hide search' : 'Re-search'"
            size="small"
            text
            :severity="showSearch ? 'primary' : 'secondary'"
            icon="pi ph ph-magnifying-glass"
            v-tooltip.top="'Search compositions for this peak in the panel below'"
            @click="showSearch = !showSearch"
          />
        </div>
      </section>
      <section v-else-if="app.data.peak.focused" class="inspector">
        <div class="insp-head">
          <div class="insp-formula">Unassigned</div>
          <BaseTierTag tier="unassigned" />
        </div>
        <div class="insp-sub">m/z {{ num.mz.format(app.data.peak.focused.mz) }}</div>
        <div class="insp-actions">
          <Button
            :label="showSearch ? 'Hide search' : 'Re-search'"
            size="small"
            text
            :severity="showSearch ? 'primary' : 'secondary'"
            icon="pi ph ph-magnifying-glass"
            v-tooltip.top="'Search compositions for this peak in the panel below'"
            @click="showSearch = !showSearch"
          />
        </div>
      </section>
      <div v-else class="center no-peak">
        <div class="col" style="gap: 0.75rem; max-width: 40ch; text-align: center; opacity: 0.6">
          <span class="pi ph ph-cursor-click" style="font-size: 1.4rem" />
          <i>Select a peak in the spectrum or ledger to inspect its assignment.</i>
        </div>
      </div>
    </div>
</template>

<style scoped>
.assign-root {
  /* Breathing room from the splitter gutter on the right. */
  padding: 0 0.75rem 0 0;
}

/* Peak inspector: the committed assignment for the focused peak. */
.inspector {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--p-content-border-color, #e3e6ec);
  border-radius: 8px;
  background: var(--p-content-background, transparent);
  width: 100%;
}
.insp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.insp-formula {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 1.35rem;
  font-weight: 700;
}
.insp-sub {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.9rem;
  opacity: 0.7;
}
.insp-sub .src {
  text-transform: capitalize;
}
.evidence {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.4rem 1rem;
}
.ev {
  display: flex;
  flex-direction: column;
  font-family: var(--font-mono, ui-monospace, monospace);
}
.ev .k {
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.55;
}
.ev .v {
  font-size: 0.98rem;
  font-variant-numeric: tabular-nums;
}
.alts {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.alts-label {
  font-size: 0.7rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.55;
}
.alt {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.6rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.86rem;
  padding: 0.15rem 0.2rem;
  border-bottom: 1px solid var(--p-content-border-color, #eef0f4);
  border-radius: 3px;
  cursor: default;
}
.alt:hover {
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.alt .s {
  opacity: 0.6;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.alt .no-stats {
  opacity: 0.5;
}
.insp-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

/* Isotopologue envelope of the focused assignment (M0 + M+1, M+2 ...). */
.isotopologues {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.iso-head,
.iso-row {
  display: grid;
  /* Fixed content tracks + a trailing spacer so the numeric columns stay snug
     instead of the m/z column stretching across the full-width card. */
  grid-template-columns: 4.5rem 6rem 3.5rem 3.5rem 1fr;
  gap: 0.5rem;
  align-items: baseline;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85rem;
  padding: 0.15rem 0.3rem;
}
.iso-head {
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.5;
}
.iso-rows {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  max-height: 12rem;
  overflow-y: auto;
}
.iso-row {
  border-radius: 4px;
  cursor: pointer;
  font-variant-numeric: tabular-nums;
}
.iso-row:hover {
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.iso-row.current {
  background: color-mix(in srgb, var(--p-primary-color, #6366f1) 14%, transparent);
}
.iso-row .iso-label {
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}
.iso-row .iso-err,
.iso-row .iso-rel {
  opacity: 0.7;
  text-align: right;
}
/* Right-align the numeric columns (m/z, ppm, abu.) and their headers so the
   values form a tidy block instead of drifting apart. */
.iso-row .iso-mz,
.iso-head span:not(:first-child) {
  text-align: right;
}
.iso-row.poor {
  color: var(--p-surface-400, #9aa2b1);
}
.poor-icon {
  color: var(--p-orange-500, #f59e0b);
  font-size: 0.68rem;
  margin-right: 0.2rem;
}
.tie-flag {
  color: var(--p-orange-500, #f59e0b);
  font-weight: 600;
  font-size: 0.72rem;
}
.prov-flag {
  color: var(--p-orange-500, #f59e0b);
  font-size: 0.66rem;
}
.ev .v.uncal {
  opacity: 0.55;
  font-style: italic;
}
.alts-list {
  display: flex;
  flex-direction: column;
  max-height: 11rem;
  overflow-y: auto;
}
.alts-count {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.6rem;
  opacity: 0.6;
  border: 1px solid var(--p-content-border-color, #e3e6ec);
  border-radius: 100px;
  padding: 0 0.35rem;
  margin-left: 0.2rem;
}
.no-peak {
  display: grid;
  place-items: center;
  min-height: 8rem;
}
</style>
