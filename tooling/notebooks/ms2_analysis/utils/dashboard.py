import ipywidgets as widgets
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from colorcet import glasbey_hv as colormap
from IPython.display import display

from .composition import CompositionMap
from .data_extractor import DataExtractor


MAX_FRAGMENT_TRACES = 20


class Ms2Dashboard:
    def __init__(self, data: DataExtractor, compositions: CompositionMap):
        self._data = data
        self._compositions = compositions
        self._half_iso = data.isolation_width / 2

        # Build dropdown options
        self._parent_peak_options = {
            f"{pp:.4f} m/z (HCD {','.join(str(v) for v in data.hcd_energy_map[pp])}V)": pp
            for pp in data.parent_peaks
        }

        # Figures
        self._fig_survey = go.FigureWidget()
        self._fig_survey.update_layout(
            title="Averaged Survey Spectrum (MS1)",
            height=300,
            xaxis_title="m/z",
            yaxis_title="Intensity",
            margin=dict(l=60, r=20, t=40, b=40),
        )

        self._fig_fragments = go.FigureWidget()
        self._fig_fragments.update_layout(
            title="Averaged Fragment Spectrum (MS2)",
            height=300,
            xaxis_title="m/z",
            yaxis_title="Intensity",
            margin=dict(l=60, r=20, t=40, b=40),
        )

        self._fig_timeseries = go.FigureWidget()
        self._fig_timeseries.update_layout(
            title="Fragment Timeseries (normalized by parent)",
            height=350,
            xaxis_title="Time",
            yaxis_title="Relative Intensity",
            margin=dict(l=60, r=20, t=40, b=40),
        )

        # Widgets
        self._parent_dropdown = widgets.Dropdown(
            options=self._parent_peak_options,
            description="Parent peak:",
            style={"description_width": "auto"},
            layout=widgets.Layout(width="350px"),
        )
        self._info_label = widgets.HTML(value="")
        self._parent_dropdown.observe(self._update, names="value")

        self._dashboard = widgets.VBox(
            [
                widgets.HBox(
                    [self._parent_dropdown, self._info_label],
                    layout=widgets.Layout(align_items="center"),
                ),
                self._fig_survey,
                self._fig_fragments,
                self._fig_timeseries,
            ]
        )

    def show(self, timeseries=False):
        """Display the dashboard in the notebook."""
        self._update()
        children = [
            widgets.HBox(
                [self._parent_dropdown, self._info_label],
                layout=widgets.Layout(align_items="center"),
            ),
            self._fig_survey,
            self._fig_fragments,
        ]
        if timeseries:
            children.append(self._fig_timeseries)
        self._dashboard.children = tuple(children)
        display(self._dashboard)

    @staticmethod
    def _make_stem_traces(
        mz,
        intensity,
        color="steelblue",
        name="Peaks",
        highlight_mz=None,
        highlight_tol=0.01,
    ):
        """Create stem-plot traces: vertical lines for a centroided spectrum."""
        xs, ys = [], []
        for m, i in zip(mz, intensity):
            xs.extend([m, m, None])
            ys.extend([0, i, None])

        traces = [
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color=color, width=1),
                name=name,
                showlegend=False,
                hoverinfo="skip",
            ),
            go.Scatter(
                x=mz,
                y=intensity,
                mode="markers",
                marker=dict(size=4, color=color),
                name=name,
                hovertemplate="m/z: %{x:.4f}<br>Intensity: %{y:.2e}<extra></extra>",
            ),
        ]

        if highlight_mz is not None:
            idx = np.argmin(np.abs(mz - highlight_mz))
            if abs(mz[idx] - highlight_mz) < highlight_tol:
                traces.append(
                    go.Scatter(
                        x=[mz[idx]],
                        y=[intensity[idx]],
                        mode="markers",
                        marker=dict(size=12, color="orange", symbol="diamond"),
                        name="Parent peak",
                        hovertemplate="Parent m/z: %{x:.4f}<br>Intensity: %{y:.2e}<extra></extra>",
                    )
                )

        return traces

    def _update(self, change=None):
        pp = self._parent_dropdown.value
        d = self._data
        half_iso = self._half_iso

        # --- Info label ---
        self._info_label.value = (
            f"&emsp; <b>Isolation width:</b> {d.isolation_width} m/z"
        )

        # --- Composition data (needed by both MS1 and MS2 charts) ---
        ms2_spec = d.ms2_spectra[pp]
        comp_df = self._compositions.matches.get(pp, pd.DataFrame())
        comp_mzs = (
            comp_df["mz"].values
            if not comp_df.empty and "mz" in comp_df.columns
            else np.array([])
        )
        comp_ions = (
            comp_df["ion"].values
            if not comp_df.empty and "ion" in comp_df.columns
            else np.array([])
        )

        # Look up parent peak composition from MS2 fragment matches
        parent_ion_label = None
        if len(comp_mzs) > 0:
            idx = np.argmin(np.abs(comp_mzs - pp))
            if abs(comp_mzs[idx] - pp) < half_iso:
                ion = comp_ions[idx]
                if pd.notna(ion) and str(ion).strip() and ion != "---":
                    parent_ion_label = str(ion).strip()

        # --- Survey spectrum (MS1 within isolation window) ---
        mz = d.ms1_spectrum.mz
        intensity = d.ms1_spectrum.intensity
        within = np.abs(mz - pp) <= half_iso
        mz_w, int_w = mz[within], intensity[within]
        ms1_y_max = max(float(np.max(int_w)), 1.0) if len(int_w) > 0 else 1.0
        ms1_label_offset = 0.03 * ms1_y_max

        with self._fig_survey.batch_update():
            self._fig_survey.data = []
            if len(mz_w) > 0:
                for t in self._make_stem_traces(
                    mz_w,
                    int_w,
                    color="steelblue",
                    name="MS1",
                    highlight_mz=pp,
                    highlight_tol=half_iso,
                ):
                    self._fig_survey.add_trace(t)
                self._fig_survey.update_xaxes(range=[pp - half_iso, pp + half_iso])

                # Annotate parent peak with its ion composition
                if parent_ion_label is not None:
                    pidx = np.argmin(np.abs(mz_w - pp))
                    self._fig_survey.add_trace(
                        go.Scatter(
                            x=[float(mz_w[pidx])],
                            y=[float(int_w[pidx]) + ms1_label_offset],
                            mode="text",
                            text=[parent_ion_label],
                            textposition="top center",
                            textfont=dict(size=13),
                            showlegend=False,
                            cliponaxis=False,
                            hoverinfo="skip",
                        )
                    )
                self._fig_survey.update_layout(yaxis_range=[0, ms1_y_max * 1.15])
            self._fig_survey.update_layout(uirevision=str(pp))

        # --- Fragment spectrum (MS2) ---

        with self._fig_fragments.batch_update():
            self._fig_fragments.data = []
            if ms2_spec.mz.size > 0:
                ms2_y_max = max(float(np.max(ms2_spec.intensity)), 1.0)
                ms2_label_offset = 0.03 * ms2_y_max
                for t in self._make_stem_traces(
                    ms2_spec.mz, ms2_spec.intensity, color="seagreen", name="MS2"
                ):
                    self._fig_fragments.add_trace(t)

                # Add composition labels above assigned peaks
                if len(comp_ions) == len(ms2_spec.mz):
                    label_mzs, label_ints, label_texts = [], [], []
                    for i, ion in enumerate(comp_ions):
                        if pd.notna(ion) and str(ion).strip() and ion != "---":
                            label_mzs.append(float(ms2_spec.mz[i]))
                            label_ints.append(
                                float(ms2_spec.intensity[i]) + ms2_label_offset
                            )
                            label_texts.append(str(ion))
                    if label_texts:
                        self._fig_fragments.add_trace(
                            go.Scatter(
                                x=label_mzs,
                                y=label_ints,
                                mode="text",
                                text=label_texts,
                                textposition="top center",
                                textfont=dict(size=13),
                                showlegend=False,
                                cliponaxis=False,
                                hoverinfo="skip",
                            )
                        )
                self._fig_fragments.update_layout(yaxis_range=[0, ms2_y_max * 1.15])
            self._fig_fragments.update_layout(uirevision=str(pp))

        # --- Fragment timeseries (normalized) ---
        norm_ts = d.normalized_ms2_timeseries.get(pp, pd.DataFrame())
        with self._fig_timeseries.batch_update():
            self._fig_timeseries.data = []
            if not norm_ts.empty:
                max_vals = norm_ts.max(axis=1).sort_values(ascending=False)
                top_mzs = max_vals.head(MAX_FRAGMENT_TRACES).index

                for i, frag_mz in enumerate(top_mzs):
                    row = norm_ts.loc[frag_mz]
                    rgb = colormap[i % len(colormap)]
                    color = (
                        f"rgb({int(rgb[0]*255)},{int(rgb[1]*255)},{int(rgb[2]*255)})"
                    )
                    x_str = [
                        t.isoformat() if hasattr(t, "isoformat") else str(t)
                        for t in row.index
                    ]

                    ion_label = None
                    if len(comp_mzs) > 0:
                        idx = np.argmin(np.abs(comp_mzs - frag_mz))
                        if abs(comp_mzs[idx] - frag_mz) < 0.01:
                            ion = comp_ions[idx]
                            if pd.notna(ion) and str(ion).strip() and ion != "---":
                                ion_label = str(ion).strip()
                    trace_name = (
                        f"{frag_mz:.4f} m/z ({ion_label})"
                        if ion_label
                        else f"{frag_mz:.4f} m/z"
                    )

                    self._fig_timeseries.add_trace(
                        go.Scatter(
                            x=x_str,
                            y=row.values.astype(float),
                            mode="lines",
                            name=trace_name,
                            line=dict(color=color, width=1.5),
                            hovertemplate=f"m/z {frag_mz:.4f}<br>"
                            "Time: %{x}<br>Rel. Int.: %{y:.4f}<extra></extra>",
                        )
                    )
            self._fig_timeseries.update_layout(uirevision=str(pp))
