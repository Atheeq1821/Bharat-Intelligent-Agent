"""Chart generation — returns base64-encoded PNG data URIs."""

import base64
import io
import json

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

_INDIGO = "#6366f1"
_INDIGO_LIGHT = "#818cf8"
_BG = "#0f172a"
_PANEL = "#1e293b"
_TEXT = "#f1f5f9"
_MUTED = "#94a3b8"


def _style_axes(ax: plt.Axes, title: str, x_label: str, y_label: str) -> None:
    ax.set_facecolor(_PANEL)
    ax.set_title(title, color=_TEXT, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(x_label, color=_MUTED, fontsize=10)
    ax.set_ylabel(y_label, color=_MUTED, fontsize=10)
    ax.tick_params(colors=_MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.yaxis.grid(True, color="#334155", linewidth=0.6, linestyle="--")
    ax.set_axisbelow(True)


def _to_png_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=_BG)
    buf.seek(0)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode()


def _fmt_inr(val: float) -> str:
    """Format large numbers as ₹X.XL (lakh) or ₹X.XCr (crore)."""
    if val >= 10_000_000:
        return f"₹{val/10_000_000:.1f}Cr"
    if val >= 100_000:
        return f"₹{val/100_000:.1f}L"
    return f"₹{val:,.0f}"


def create_chart(
    data_json: str,
    chart_type: str = "bar",
    title: str = "Chart",
    x_label: str = "",
    y_label: str = "",
) -> str:
    """
    Generate a chart from JSON data and return a base64 PNG data URI.

    data_json: JSON array of objects, e.g.
        '[{"month": "Jan", "revenue": 1300000}, ...]'
    chart_type: "bar" | "line" | "pie" | "horizontal_bar"
    """
    try:
        rows = json.loads(data_json) if isinstance(data_json, str) else data_json
        if not rows or not isinstance(rows, list):
            return "error: data must be a non-empty JSON array"

        keys = list(rows[0].keys())
        x_key = keys[0]
        y_key = keys[1] if len(keys) > 1 else keys[0]

        x_vals = [str(r[x_key]) for r in rows]
        y_vals = [float(r.get(y_key, 0)) for r in rows]
        is_currency = any(k in y_key.lower() for k in ("amount", "revenue", "total", "balance", "price", "payment"))

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor(_BG)

        if chart_type in ("bar", "horizontal_bar"):
            if chart_type == "horizontal_bar":
                bars = ax.barh(x_vals, y_vals, color=_INDIGO, edgecolor=_INDIGO_LIGHT, linewidth=0.5)
                for bar, val in zip(bars, y_vals):
                    ax.text(
                        bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                        _fmt_inr(val) if is_currency else f"{val:,.0f}",
                        va="center", color=_TEXT, fontsize=8,
                    )
            else:
                bars = ax.bar(x_vals, y_vals, color=_INDIGO, edgecolor=_INDIGO_LIGHT, linewidth=0.5)
                for bar, val in zip(bars, y_vals):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.015,
                        _fmt_inr(val) if is_currency else f"{val:,.0f}",
                        ha="center", va="bottom", color=_TEXT, fontsize=8,
                    )
                plt.xticks(rotation=30, ha="right")

        elif chart_type == "line":
            ax.plot(x_vals, y_vals, color=_INDIGO, linewidth=2.5, marker="o", markersize=6, markerfacecolor=_INDIGO_LIGHT)
            ax.fill_between(range(len(x_vals)), y_vals, alpha=0.15, color=_INDIGO)
            ax.set_xticks(range(len(x_vals)))
            ax.set_xticklabels(x_vals, rotation=30, ha="right")
            for i, (xi, yi) in enumerate(zip(x_vals, y_vals)):
                ax.annotate(
                    _fmt_inr(yi) if is_currency else f"{yi:,.0f}",
                    (i, yi), textcoords="offset points", xytext=(0, 8),
                    ha="center", color=_TEXT, fontsize=8,
                )

        elif chart_type == "pie":
            palette = [_INDIGO, _INDIGO_LIGHT, "#a5b4fc", "#c7d2fe", "#e0e7ff", "#4f46e5", "#4338ca"]
            wedges, texts, autotexts = ax.pie(
                y_vals, labels=x_vals, autopct="%1.1f%%",
                colors=palette[: len(y_vals)],
                textprops={"color": _TEXT, "fontsize": 9},
                wedgeprops={"edgecolor": _BG, "linewidth": 1.5},
            )
            for at in autotexts:
                at.set_color(_BG)
                at.set_fontweight("bold")

        _style_axes(ax, title, x_label or x_key, y_label or (y_key if chart_type != "pie" else ""))
        plt.tight_layout()
        return _to_png_b64(fig)

    except Exception as e:
        return f"error generating chart: {e}"
