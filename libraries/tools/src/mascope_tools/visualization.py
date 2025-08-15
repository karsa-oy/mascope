import matplotlib.pyplot as plt
import numpy as np
from alignment.calibration import CentroidedSpectrum
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import ipywidgets as widgets


def plot_mz_shifts_ppm(
    spectra: list[CentroidedSpectrum], corrected_spectra: list[CentroidedSpectrum]
) -> None:
    """Plots the m/z shifts in ppm before and after alignment correction.

    :param spectra: List of original spectra before alignment correction.
    :type spectra: list[CentroidedSpectrum]
    :param corrected_spectra: List of corrected spectra after alignment correction.
    :type corrected_spectra: list[CentroidedSpectrum]
    """
    # Flatten all m/z values before and after
    all_mzs_before = np.concatenate([s.mz for s in spectra])
    all_mzs_after = np.concatenate([s.mz for s in corrected_spectra])

    diff_ppm = (all_mzs_after - all_mzs_before) / all_mzs_before * 1e6

    plt.figure(figsize=(6, 3))
    plt.scatter(all_mzs_before, diff_ppm, s=2, alpha=0.3)
    plt.xlabel("m/z (before)")
    plt.ylabel("Δm/z (ppm, after - before)")
    plt.title("Alignment Correction Across m/z Range")

    plt.show()


def flatten_spectra(specs):
    """Flatten spectra into arrays of mz, intensity."""
    total_len = np.sum(s.mz.size for s in specs)
    mz = np.empty(total_len)
    intensity = np.empty(total_len)
    idx = 0
    for s in specs:
        n = len(s.mz)
        mz[idx : idx + n] = s.mz
        intensity[idx : idx + n] = s.intensity
        idx += n
    return mz, intensity


def compare_initial_and_corrected_spectra(
    spectra: list[CentroidedSpectrum],
    corrected_spectra: list[CentroidedSpectrum],
    total_averaged_signal: dict[str, np.ndarray],
) -> widgets.interact:
    """Compare initial and corrected spectra using an interactive plot.

    :param spectra: List of original spectra before alignment correction.
    :type spectra: list[CentroidedSpectrum]
    :param corrected_spectra: List of corrected spectra after alignment correction.
    :type corrected_spectra: list[CentroidedSpectrum]
    :param total_averaged_signal: Averaged signal data containing m/z and intensity.
    :type total_averaged_signal: dict[str, np.ndarray]
    :return: Interactive widget for selecting m/z range and plotting spectra.
    :rtype: widgets.interact
    """
    # Precompute flattened arrays for performance
    mz_before, int_before = flatten_spectra(spectra)
    mz_after, int_after = flatten_spectra(corrected_spectra)

    window_factor = 2
    preliminary_sum_spec = corrected_spectra.compute_sum_spectrum(
        average=True, window_factor=window_factor
    )
    mz_binned = preliminary_sum_spec.mz
    int_binned = preliminary_sum_spec.intensity
    fwhm_binned = mz_binned / preliminary_sum_spec.resolution

    # Find all unique m/z values with signal or centroids
    valid_mz = np.unique(
        np.concatenate(
            [
                mz_before[int_before > 0],
                mz_after[int_after > 0],
                mz_binned[int_binned > 0],
                total_averaged_signal["mz"][total_averaged_signal["intensity"] > 0],
            ]
        )
    )
    valid_mz = valid_mz[(valid_mz >= np.min(valid_mz)) & (valid_mz <= np.max(valid_mz))]

    mz_slider = widgets.SelectionSlider(
        options=[float(f"{mz:.4f}") for mz in valid_mz],
        value=float(f"{valid_mz[0]:.4f}"),
        description="m/z window start",
        layout=widgets.Layout(width="80%"),
        continuous_update=False,
    )

    def plot_spectra_points(mz_start):
        window_width = 0.1
        mz_end = mz_start + window_width

        centroid_mask_before = (mz_before >= mz_start) & (mz_before <= mz_end)
        centroid_mask_after = (mz_after >= mz_start) & (mz_after <= mz_end)
        centroid_mask_binned = (mz_binned >= mz_start) & (mz_binned <= mz_end)
        averaged_spec_mask = (total_averaged_signal["mz"] >= mz_start) & (
            total_averaged_signal["mz"] <= mz_end
        )

        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("Original", "Corrected"),
            shared_xaxes=True,
            shared_yaxes=True,
        )

        for row in [1, 2]:
            fig.add_trace(
                go.Scatter(
                    x=total_averaged_signal["mz"][averaged_spec_mask],
                    y=total_averaged_signal["intensity"][averaged_spec_mask],
                    mode="lines",
                    line=dict(color="black", width=1),
                    name="Averaged Spectrum",
                    showlegend=True,
                ),
                row=row,
                col=1,
            )

            # --- Semitransparent vertical red bands for binned centroids ---
            for x, y, w in zip(
                mz_binned[centroid_mask_binned],
                int_binned[centroid_mask_binned],
                fwhm_binned[centroid_mask_binned],
            ):
                fig.add_shape(
                    type="rect",
                    xref="x",
                    yref="paper",
                    x0=x - w / 2,
                    x1=x + w / 2,
                    y0=0,
                    y1=y,
                    fillcolor="red",
                    opacity=0.2,
                    line_width=0,
                    layer="below",
                    row=row,
                    col=1,
                )

        # Add a single dummy trace for legend entry
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line=dict(color="red", width=5),
                name="Centroid Aggregation Width = FWHM",
                showlegend=True,
                opacity=0.2,
            ),
            row=2,
            col=1,
        )

        # --- Before centroids ---
        for x, y in zip(
            mz_before[centroid_mask_before], int_before[centroid_mask_before]
        ):
            fig.add_trace(
                go.Scatter(
                    x=[x, x],
                    y=[0, y],
                    mode="lines",
                    line=dict(color="darkgreen", width=1),
                    name="Centroids",
                    showlegend=True,
                ),
                row=1,
                col=1,
            )

        # --- After centroids ---
        for x, y in zip(mz_after[centroid_mask_after], int_after[centroid_mask_after]):
            fig.add_trace(
                go.Scatter(
                    x=[x, x],
                    y=[0, y],
                    mode="lines",
                    line=dict(color="darkgreen", width=1),
                    showlegend=False,
                ),
                row=2,
                col=1,
            )

        # --- Binned centroids ---
        for x, y in zip(
            mz_binned[centroid_mask_binned], int_binned[centroid_mask_binned]
        ):
            fig.add_trace(
                go.Scatter(
                    x=[x, x],
                    y=[0, y],
                    mode="lines",
                    line=dict(color="red", width=3),
                    name="Aggregated Centroid",
                    showlegend=True,
                ),
                row=2,
                col=1,
            )

        # Remove duplicate legend entries
        unique_names = set()
        for trace in fig.data:
            name = trace.name
            if name in unique_names:
                trace.showlegend = False
            else:
                unique_names.add(name)

        # Remove grids from both subplots
        fig.update_xaxes(showgrid=False, row=1, col=1)
        fig.update_xaxes(showgrid=False, row=2, col=1)
        fig.update_yaxes(showgrid=False, row=1, col=1)
        fig.update_yaxes(showgrid=False, row=2, col=1)

        fig.update_xaxes(title_text="m/z", row=1, col=1)
        fig.update_xaxes(title_text="m/z", row=2, col=1)
        fig.update_yaxes(title_text="Intensity", row=1, col=1)
        fig.update_yaxes(title_text="Intensity", row=2, col=1)
        fig.update_layout(
            height=500,
            width=800,
            title_text=f"Spectra Points ({mz_start:.1f}–{mz_end:.1f} m/z)",
            margin=dict(t=60, b=10, l=10, r=10),
        )
        fig.show()

    return widgets.interact(plot_spectra_points, mz_start=mz_slider)
