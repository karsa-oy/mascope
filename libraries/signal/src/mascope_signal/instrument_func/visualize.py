from functools import partial
from xarray import DataArray
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from mascope_signal.fitting import gen_peak

subtitles = ("FWHM", "Chosen peak", "Resolution function")


def visualize(
    p_mzs: np.ndarray,
    p_fwhms: np.ndarray,
    p_fwhms_fit: np.ndarray,
    ndev: int,
    res_fun: partial,
) -> go.Figure:
    """Visualize the FWHM, chosen peak, and resolution function.

    This function creates a Plotly figure with subplots to visualize the Full Width at Half Maximum (FWHM),
    the chosen peak, and the resolution function based on the provided data.

    :param p_mzs: Array of m/z values.
    :type p_mzs: np.ndarray
    :param p_fwhms: Array of FWHM values corresponding to the m/z values.
    :type p_fwhms: np.ndarray
    :param p_fwhms_fit: Array of fitted FWHM values corresponding to the m/z values.
    :type p_fwhms_fit: np.ndarray
    :param ndev: Number of standard deviations to filter out outliers in the FWHM fit.
    :type ndev: int
    :param res_fun: Function to calculate the resolution based on m/z values.
    :type res_fun: partial
    :return: A Plotly figure with subplots visualizing the FWHM, chosen peak, and resolution function.
    :rtype: go.Figure
    """
    # Get residuals and standard deviation
    residuals = p_fwhms - p_fwhms_fit
    std_dev = np.std(residuals)
    is_outlier = (residuals > ndev * std_dev) | (residuals < -ndev * std_dev)

    # Remove outliers
    p_fwhms_filt = np.array(p_fwhms, dtype=np.double)[~is_outlier]
    mass = np.array(p_mzs, dtype=np.double)[~is_outlier]
    resolution = mass / p_fwhms_filt

    # Ensure data is sorted by x values
    sorted_indices = np.argsort(p_mzs)
    p_mzs_sort = p_mzs[sorted_indices]
    p_fwhms_fit_sort = p_fwhms_fit[sorted_indices]

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{}, {}], [{"colspan": 2}, None]],
        subplot_titles=subtitles,
    )

    # FWHM traces
    fig.add_traces(
        [
            go.Scatter(x=p_mzs, y=p_fwhms, mode="markers", name="True FWHM"),
            go.Scatter(
                x=p_mzs_sort,
                y=p_fwhms_fit_sort,
                mode="lines",
                line=dict(dash="dash"),
                name="Approximation",
            ),
            go.Scatter(
                x=np.concatenate([p_mzs_sort, p_mzs_sort[::-1]]),
                y=np.concatenate(
                    [
                        p_fwhms_fit_sort + ndev * std_dev,
                        (p_fwhms_fit_sort - ndev * std_dev)[::-1],
                    ]
                ),
                fill="toself",
                fillcolor="rgba(120, 120, 120, 0.2)",
                line=dict(color="rgba(0, 0, 0, 0)"),
                showlegend=False,
            ),
        ],
        rows=1,
        cols=1,
    )

    # Fitted resolution function traces
    mass_range = np.linspace(min(p_mzs), max(p_mzs), 100)
    fig.add_traces(
        [
            go.Scatter(
                x=mass_range,
                y=res_fun(mass_range),
                mode="lines",
                line=dict(color="red"),
                name="Fitted resolution function",
            ),
            go.Scatter(
                x=p_mzs,
                y=p_mzs / p_fwhms,
                mode="markers",
                marker=dict(color="grey"),
                name="Omitted pairs",
            ),
            go.Scatter(
                x=mass,
                y=resolution,
                mode="markers",
                marker=dict(color="black"),
                name="Used mass/resolution pairs",
            ),
        ],
        rows=2,
        cols=1,
    )

    # Chosen peak traces
    chosen_peak_trace = go.Scatter(
        x=[0], y=[0], name="Chosen peak", line=dict(color="coral")
    )
    fit_signal_trace = go.Scatter(
        x=[0],
        y=[0],
        name="Fitted signal",
        line=dict(color="steelblue", width=4, dash="dash"),
    )
    residuals_trace = go.Scatter(
        x=[0],
        y=[0],
        name="Residuals",
        fill="tozeroy",
        fillcolor="rgba(70, 130, 180, 0.5)",
        line=dict(color="rgba(0, 0, 0, 0)"),
    )
    fig.add_traces(
        [chosen_peak_trace, fit_signal_trace, residuals_trace], rows=1, cols=2
    )

    # Update layout
    fig.update_xaxes(title_text="mz", row=1, col=1)
    fig.update_yaxes(title_text="FWHM", row=1, col=1)
    fig.update_xaxes(title_text="mz", row=1, col=2)
    fig.update_yaxes(title_text="Counts", row=1, col=2)
    fig.update_xaxes(title_text="mz", row=2, col=1)
    fig.update_yaxes(title_text="Resolution", row=2, col=1)
    fig.update_layout(
        height=450, width=1000, margin=go.layout.Margin(l=30, r=30, b=30, t=30)
    )

    return fig


def update_chosen_peak(
    points: dict,
    fig: go.Figure,
    sum_signal: DataArray,
    fit_poss: np.ndarray,
    fit_heis: np.ndarray,
    res_fun: partial,
    ps: dict,
) -> go.Figure:
    """Update the chosen peak window.

    :param points: Click data points from the interactive plot.
    :type points: dict
    :param fig: Plotly figure to update.
    :type fig: go.Figure
    :param sum_signal: Sum signal xarray.
    :type sum_signal: DataArray
    :param fit_poss: Array of fitted peak positions.
    :type fit_poss: np.ndarray
    :param fit_heis: Array of fitted peak heights.
    :type fit_heis: np.ndarray
    :param res_fun: Function to calculate the resolution based on m/z values.
    :type res_fun: partial
    :param ps: Peak shape.
    :type ps: dict
    :return: Updated Plotly figure.
    :rtype: go.Figure
    """
    if points["x"]:
        # Clear peak shapes from the figure
        fig.layout.shapes = []

        # Clean annotations
        fig.layout.annotations = [
            i for i in fig.layout.annotations if i.text in subtitles
        ]

        # Get chosen m/z value
        chosen_peak_val = points["x"]

        # Calculate chosen peak window width
        dmz = 3 * chosen_peak_val / res_fun(chosen_peak_val)

        # Filter spectra window to plot
        chosen_peak = sum_signal.sel(
            mz=slice(chosen_peak_val - dmz, chosen_peak_val + dmz)
        )
        mz_window_x = chosen_peak.mz.values
        mz_window_y = chosen_peak.values

        # Fitted peak mask
        fit_peak_mask = (chosen_peak_val - dmz < fit_poss) & (
            fit_poss < chosen_peak_val + dmz
        )
        fit_poss_filt = fit_poss[fit_peak_mask]
        fit_heis_filt = fit_heis[fit_peak_mask]

        fit_y = np.zeros_like(mz_window_x)
        for i, mz_val in enumerate(fit_poss_filt):
            # Add fitted peak to fit_y, plot its position and m/z value
            fit_y += gen_peak(
                mz_window_x,
                mz_val,
                fit_heis_filt[i],
                pres=res_fun(mz_val),
                ps=ps,
            )
            fig.add_shape(
                type="line",
                x0=mz_val,
                x1=mz_val,
                y0=0,
                y1=fit_heis_filt[i],
                line=dict(width=2),
                xref="x2",
                yref="y2",
            )
            fig.add_annotation(
                x=mz_val,
                y=fit_heis_filt[i],
                text=f"{mz_val:.3f}",
                showarrow=False,
                xref="x2",
                yref="y2",
                yshift=10,
            )

        residuals = mz_window_y - fit_y

        # Update traces in the chosen peak window
        fig.update_traces(
            {"x": mz_window_x, "y": mz_window_y},
            selector=lambda trace: trace.name == "Chosen peak",
        )
        fig.update_traces(
            {"x": mz_window_x, "y": fit_y},
            selector=lambda trace: trace.name == "Fitted signal",
        )
        fig.update_traces(
            {"x": mz_window_x, "y": residuals},
            selector=lambda trace: trace.name == "Residuals",
        )

    return fig
