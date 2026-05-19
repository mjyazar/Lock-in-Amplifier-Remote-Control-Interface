import csv
import io
import logging
from datetime import datetime

import dash
import plotly.graph_objects as go
from dash import html, dcc, dash_table, Input, Output, State

logger = logging.getLogger(__name__)

# ── In-browser log capture ─────────────────────────────────────────────────────
class _WebLogHandler(logging.Handler):
    _MAX = 500

    def __init__(self):
        super().__init__()
        self._records = []
        self.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record):
        if record.name.startswith("pyvisa"):
            return
        self._records.append((record.levelname, self.format(record)))
        if len(self._records) > self._MAX:
            self._records = self._records[-self._MAX:]

    def get_records(self):
        return list(self._records)

    def clear(self):
        self._records.clear()


_log_handler = _WebLogHandler()

# ── Design tokens ─────────────────────────────────────────────────────────────
_BLUE       = "#1ba4f9"
_BLUE_DARK  = "#022338"
_BLUE_MID   = "#0a3a5c"
_BLUE_LIGHT = "#e8f4f8"
_GREEN      = "#2e7d32"
_RED        = "#c62828"
_AMBER      = "#e65100"
_BG         = "#edf0f5"
_SURFACE    = "#ffffff"
_BORDER     = "#dee2e6"
_TEXT       = "#212529"
_MUTED      = "#6c757d"

# ── Row element styles ────────────────────────────────────────────────────────
_LABEL = {
    "fontWeight": "600", "minWidth": "170px", "display": "inline-block",
    "fontSize": "0.87em", "color": _TEXT,
}
_DISPLAY = {
    "width": "200px", "display": "inline-block",
    "fontFamily": "monospace", "color": _BLUE, "fontSize": "0.87em",
    "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap",
    "verticalAlign": "middle",
}
_STATUS = {"marginLeft": "8px", "fontFamily": "monospace", "fontSize": "0.80em"}

_NUM_INPUT = {
    "width": "175px", "margin": "0 6px", "padding": "5px 8px",
    "border": f"1px solid {_BORDER}", "borderRadius": "4px", "fontSize": "0.87em",
    "boxSizing": "border-box",
}
_NUM_WIDE = {
    **_NUM_INPUT, "width": "225px",
}
_NUM_INVALID = {
    **_NUM_INPUT, "border": f"2px solid {_RED}",
    "boxShadow": f"0 0 0 3px rgba(198,40,40,0.15)",
}
_NUM_WIDE_INVALID = {
    **_NUM_WIDE, "border": f"2px solid {_RED}",
    "boxShadow": f"0 0 0 3px rgba(198,40,40,0.15)",
}

_DD_WRAP = {
    "width": "220px", "display": "inline-block", "margin": "0 6px",
    "verticalAlign": "middle",
}
_BTN_READ = {
    "marginRight": "8px", "padding": "4px 12px",
    "background": "#f1f3f5", "border": f"1px solid {_BORDER}",
    "borderRadius": "4px", "cursor": "pointer", "fontSize": "0.82em",
    "color": _TEXT,
}
_BTN_SET = {
    "padding": "4px 12px", "background": _BLUE, "color": "#fff",
    "border": "none", "borderRadius": "4px", "cursor": "pointer", "fontSize": "0.82em",
}
_ROW = {
    "display": "flex", "alignItems": "center",
    "padding": "7px 0", "borderBottom": f"1px solid {_BORDER}",
}


# ── Status span helpers ────────────────────────────────────────────────────────
def _ok(msg):   return html.Span(msg, style={"color": _GREEN})
def _err(msg):  return html.Span(str(msg), style={"color": _RED})
def _warn(msg): return html.Span(msg, style={"color": _AMBER})


# ── Row builders ───────────────────────────────────────────────────────────────
def _number_row(label, disp, rbtn, inp, sbtn, stat, placeholder="", step=None, wide=False):
    base = _NUM_WIDE if wide else _NUM_INPUT
    kw = dict(id=inp, type="number", placeholder=placeholder, debounce=False, style=base)
    if step is not None:
        kw["step"] = step
    return html.Div([
        html.Span(label, style=_LABEL),
        html.Span("—", id=disp, style=_DISPLAY),
        html.Button("Read", id=rbtn, n_clicks=0, style=_BTN_READ),
        dcc.Input(**kw),
        html.Button("Set", id=sbtn, n_clicks=0, style=_BTN_SET),
        html.Span("", id=stat, style=_STATUS),
    ], style=_ROW)


def _dropdown_row(label, disp, rbtn, inp, sbtn, stat, options):
    return html.Div([
        html.Span(label, style=_LABEL),
        html.Span("—", id=disp, style=_DISPLAY),
        html.Button("Read", id=rbtn, n_clicks=0, style=_BTN_READ),
        html.Div(
            dcc.Dropdown(id=inp, options=options, placeholder="Select…",
                         clearable=False, style={"width": "100%", "fontSize": "0.87em"}),
            style=_DD_WRAP,
        ),
        html.Button("Set", id=sbtn, n_clicks=0, style=_BTN_SET),
        html.Span("", id=stat, style=_STATUS),
    ], style=_ROW)


def create_app(amp):
    logging.getLogger().addHandler(_log_handler)
    app = dash.Dash(__name__)

    # ── Option lists ──────────────────────────────────────────────────────────
    SENS_OPTS     = [{"label": v[0], "value": i} for i, v in amp.SENSITIVITY.items()]
    TC_OPTS       = [{"label": v[0], "value": i} for i, v in amp.TIME_CONSTANT.items()]
    REF_SRC_OPTS  = [{"label": "External", "value": 0}, {"label": "Internal", "value": 1}]
    REF_TRIG_OPTS = [
        {"label": "Sine zero crossing", "value": 0},
        {"label": "TTL rising edge",    "value": 1},
        {"label": "TTL falling edge",   "value": 2},
    ]
    INPUT_CFG_OPTS = [
        {"label": "A",          "value": 0}, {"label": "A−B",       "value": 1},
        {"label": "I (1 MΩ)",  "value": 2}, {"label": "I (100 MΩ)", "value": 3},
    ]
    INPUT_GND_OPTS = [{"label": "Float",  "value": 0}, {"label": "Ground", "value": 1}]
    INPUT_CPL_OPTS = [{"label": "AC",     "value": 0}, {"label": "DC",     "value": 1}]
    NOTCH_OPTS     = [
        {"label": "No filters",    "value": 0}, {"label": "Line notch",  "value": 1},
        {"label": "2× Line notch", "value": 2}, {"label": "Both filters","value": 3},
    ]
    RESERVE_OPTS = [
        {"label": "High Reserve", "value": 0},
        {"label": "Normal",       "value": 1},
        {"label": "Low Noise",    "value": 2},
    ]
    SLOPE_OPTS = [
        {"label": "6 dB/oct",  "value": 0}, {"label": "12 dB/oct", "value": 1},
        {"label": "18 dB/oct", "value": 2}, {"label": "24 dB/oct", "value": 3},
    ]
    SYNC_OPTS = [{"label": "Off", "value": 0}, {"label": "On (<200 Hz)", "value": 1}]

    DDEF_PARAM_OPTS = [
        {"label": "X",         "value": 0},  {"label": "Y",         "value": 1},
        {"label": "R",         "value": 2},  {"label": "θ",    "value": 3},
        {"label": "Noise",     "value": 4},  {"label": "Aux In 1",  "value": 5},
        {"label": "Aux In 2",  "value": 6},  {"label": "Aux In 3",  "value": 7},
        {"label": "Aux In 4",  "value": 8},  {"label": "Aux Out 1", "value": 9},
        {"label": "Aux Out 2", "value": 10}, {"label": "Phase",     "value": 11},
        {"label": "Mark",      "value": 12},
    ]
    DDEF_RATIO_OPTS = [
        {"label": "None",     "value": 0}, {"label": "Aux In 1", "value": 1},
        {"label": "Aux In 2", "value": 2}, {"label": "Aux In 3", "value": 3},
        {"label": "Aux In 4", "value": 4},
    ]
    FPOP_CH1_OPTS = [{"label": "CH1 display", "value": 0}, {"label": "X", "value": 1}]
    FPOP_CH2_OPTS = [{"label": "CH2 display", "value": 0}, {"label": "Y", "value": 1}]

    GRAPH_PARAMS = [
        {"label": "X  (in-phase, V)",        "value": "X"},
        {"label": "Y  (quadrature, V)",       "value": "Y"},
        {"label": "R  (magnitude, V)",        "value": "R"},
        {"label": "θ  (phase angle, °)",      "value": "theta"},
        {"label": "Frequency (Hz)",           "value": "frequency"},
        {"label": "Phase (°)",                "value": "phase"},
        {"label": "Sine Amplitude (Vrms)",    "value": "sine_amp"},
        {"label": "Sensitivity index",        "value": "sensitivity"},
        {"label": "Time Constant index",      "value": "time_constant"},
    ]

    # ── Label maps ────────────────────────────────────────────────────────────
    _CFG_LABELS   = {0: "A", 1: "A−B", 2: "I (1 MΩ)", 3: "I (100 MΩ)"}
    _SRC_LABELS   = {0: "External", 1: "Internal"}
    _TRIG_LABELS  = {0: "Sine zero crossing", 1: "TTL rising edge", 2: "TTL falling edge"}
    _GND_LABELS   = {0: "Float", 1: "Ground"}
    _CPL_LABELS   = {0: "AC", 1: "DC"}
    _NOTCH_LABELS = {0: "No filters", 1: "Line notch", 2: "2× Line notch", 3: "Both filters"}
    _SYNC_LABELS  = {0: "Off", 1: "On (<200 Hz)"}
    _COLS = ["timestamp","X","Y","R","theta","frequency","phase","sine_amp","harmonic",
             "ref_src","ref_trig","sensitivity","reserve","time_constant","filter_slope",
             "sync_filter","input_cfg","input_gnd","input_cpl","notch",
             "aux_in_1","aux_in_2","aux_in_3","aux_in_4"]

    def _sl(i): return amp.SENSITIVITY[i][0]
    def _tl(i): return amp.TIME_CONSTANT[i][0]
    def _rl(i): return amp.RESERVE_MODE[i]
    def _fl(i): return f"{amp.FILTER_SLOPE[i]} dB/oct"

    # ── Shared panel styles ───────────────────────────────────────────────────
    _PANEL = {
        "background": _SURFACE, "border": f"1px solid {_BORDER}",
        "borderRadius": "8px", "padding": "14px 16px", "marginBottom": "14px",
        "boxShadow": "0 1px 4px rgba(0,0,0,0.07)",
    }
    _PANEL_HDR = {
        "margin": "0 0 10px 0", "color": _BLUE_DARK, "fontSize": "0.73em",
        "fontWeight": "800", "letterSpacing": "0.12em", "textTransform": "uppercase",
        "borderBottom": f"2px solid {_BLUE}", "paddingBottom": "5px",
    }
    _SIDEBAR_BTN = {
        "width": "100%", "padding": "8px 0", "marginBottom": "6px",
        "background": "#2c3e50", "color": "#ecf0f1",
        "border": "none", "borderRadius": "6px", "cursor": "pointer",
        "fontSize": "0.85em", "fontWeight": "500",
    }
    _CONTENT_CARD = {
        "background": _SURFACE, "border": f"1px solid {_BORDER}",
        "borderRadius": "8px", "padding": "18px 22px",
        "boxShadow": "0 1px 4px rgba(0,0,0,0.07)",
    }
    _NAV_BTN = {
        "padding": "15px 22px", "color": "#7aa8c8",
        "background": "transparent", "border": "none", "cursor": "pointer",
        "fontSize": "0.88em", "fontWeight": "500", "letterSpacing": "0.03em",
        "borderBottom": "3px solid transparent",
    }
    _NAV_BTN_ACT = {
        **_NAV_BTN, "color": "#ffffff", "fontWeight": "700",
        "borderBottom": f"3px solid {_BLUE}",
    }

    # ── Sub-layout helpers ────────────────────────────────────────────────────
    def _meas_row(label, span_id):
        return html.Div([
            html.Span(label, style={
                "fontSize": "0.78em", "fontWeight": "800", "color": _MUTED,
                "letterSpacing": "0.05em", "minWidth": "22px", "display": "inline-block",
            }),
            html.Span("—", id=span_id, style={
                "fontFamily": "monospace", "color": _BLUE,
                "fontSize": "0.95em", "fontWeight": "600", "marginLeft": "10px",
            }),
        ], style={"padding": "7px 4px", "borderBottom": f"1px solid {_BORDER}"})

    def _aux_in_row(ch):
        return html.Div([
            html.Span(f"Ch {ch}", style={**_LABEL, "minWidth": "50px"}),
            html.Span("—", id=f"out-aux-in-{ch}", style={**_DISPLAY, "minWidth": "110px"}),
            html.Button("Read", id=f"btn-read-aux-in-{ch}", n_clicks=0, style=_BTN_READ),
        ], style=_ROW)

    def _aux_out_row(ch):
        return html.Div([
            html.Span(f"Ch {ch}", style={**_LABEL, "minWidth": "50px"}),
            dcc.Input(id=f"in-aux-out-{ch}", type="number",
                      placeholder="−10.500 – +10.500 V", debounce=False,
                      style={**_NUM_WIDE, "width": "200px"}),
            html.Button("Set", id=f"btn-set-aux-out-{ch}", n_clicks=0, style=_BTN_SET),
            html.Span("", id=f"status-aux-out-{ch}", style=_STATUS),
        ], style=_ROW)

    def _log_entry(level, msg):
        colors = {"DEBUG":"#484f58","INFO":"#c9d1d9","WARNING":"#d29922","ERROR":"#f85149","CRITICAL":"#ff4040"}
        return html.Div(msg, style={
            "color": colors.get(level, "#c9d1d9"),
            "fontSize": "0.73em", "fontFamily": "monospace", "lineHeight": "1.6",
            "padding": "1px 2px", "whiteSpace": "nowrap",
        })

    def _cfg_num(label, fid, placeholder=""):
        return html.Div([
            html.Label(label, style={"fontSize": "0.80em", "color": _MUTED,
                                     "display": "block", "marginBottom": "3px"}),
            dcc.Input(id=fid, type="number", placeholder=placeholder, debounce=False,
                      style={**_NUM_INPUT, "width": "100%", "margin": "0"}),
        ], style={"flex": "1", "minWidth": "180px", "marginRight": "14px", "marginBottom": "12px"})

    def _cfg_dd(label, fid, options):
        return html.Div([
            html.Label(label, style={"fontSize": "0.80em", "color": _MUTED,
                                     "display": "block", "marginBottom": "3px"}),
            dcc.Dropdown(id=fid, options=options, placeholder="Select…", clearable=True,
                         style={"fontSize": "0.87em"}),
        ], style={"flex": "1", "minWidth": "200px", "marginRight": "14px", "marginBottom": "12px"})

    # ── Tab IDs ───────────────────────────────────────────────────────────────
    _TABS = ["ref", "gain", "input", "aux", "rec", "cfg"]
    _TAB_LABELS = {
        "ref":   "Reference & Phase",
        "gain":  "Gain & Time Constant",
        "input": "Input & Filter",
        "aux":   "Auxiliary I/O",
        "rec":   "Recordings",
        "cfg":   "Configurations",
    }

    # ── Pre-build tab content sections ─────────────────────────────────────────
    _ref_content = html.Div([
        _number_row("Frequency (Hz)", "out-frequency", "btn-read-frequency",
                    "in-frequency", "btn-set-frequency", "status-frequency",
                    placeholder="0.001 – 102000.000", wide=True),
        _number_row("Phase (°)", "out-phase", "btn-read-phase",
                    "in-phase", "btn-set-phase", "status-phase",
                    placeholder="−360.00 – +729.99", wide=True),
        _number_row("Sine Amplitude (Vrms)", "out-sine-amp", "btn-read-sine-amp",
                    "in-sine-amp", "btn-set-sine-amp", "status-sine-amp",
                    placeholder="0.004 – 5.000", wide=True),
        _dropdown_row("Reference Source", "out-ref-src", "btn-read-ref-src",
                      "in-ref-src", "btn-set-ref-src", "status-ref-src", REF_SRC_OPTS),
        _dropdown_row("Reference Trigger", "out-ref-trig", "btn-read-ref-trig",
                      "in-ref-trig", "btn-set-ref-trig", "status-ref-trig", REF_TRIG_OPTS),
        _number_row("Detection Harmonic", "out-harmonic", "btn-read-harmonic",
                    "in-harmonic", "btn-set-harmonic", "status-harmonic",
                    placeholder="1 – 19999", step=1, wide=True),
    ], style=_CONTENT_CARD)

    _gain_content = html.Div([
        _dropdown_row("Sensitivity", "out-sensitivity", "btn-read-sensitivity",
                      "in-sensitivity", "btn-set-sensitivity", "status-sensitivity", SENS_OPTS),
        _dropdown_row("Reserve Mode", "out-reserve", "btn-read-reserve",
                      "in-reserve", "btn-set-reserve", "status-reserve", RESERVE_OPTS),
        _dropdown_row("Time Constant", "out-time-constant", "btn-read-time-constant",
                      "in-time-constant", "btn-set-time-constant", "status-time-constant", TC_OPTS),
        _dropdown_row("Low-Pass Filter Slope", "out-filter-slope", "btn-read-filter-slope",
                      "in-filter-slope", "btn-set-filter-slope", "status-filter-slope", SLOPE_OPTS),
        _dropdown_row("Synchronous Filter", "out-sync-filter", "btn-read-sync-filter",
                      "in-sync-filter", "btn-set-sync-filter", "status-sync-filter", SYNC_OPTS),
    ], style=_CONTENT_CARD)

    _input_content = html.Div([
        _dropdown_row("Input Configuration", "out-input-cfg", "btn-read-input-cfg",
                      "in-input-cfg", "btn-set-input-cfg", "status-input-cfg", INPUT_CFG_OPTS),
        _dropdown_row("Input Shield Grounding", "out-input-gnd", "btn-read-input-gnd",
                      "in-input-gnd", "btn-set-input-gnd", "status-input-gnd", INPUT_GND_OPTS),
        _dropdown_row("Input Coupling", "out-input-cpl", "btn-read-input-cpl",
                      "in-input-cpl", "btn-set-input-cpl", "status-input-cpl", INPUT_CPL_OPTS),
        _dropdown_row("Line Notch Filter", "out-notch", "btn-read-notch",
                      "in-notch", "btn-set-notch", "status-notch", NOTCH_OPTS),
    ], style=_CONTENT_CARD)

    _aux_content = html.Div([
        html.Div([
            html.Div([
                html.Div("Aux Inputs (V, read-only)",
                         style={"fontSize": "0.80em","color":_MUTED,"fontWeight":"700",
                                "letterSpacing":"0.05em","marginBottom":"8px"}),
                *[_aux_in_row(ch) for ch in range(1, 5)],
            ], style={"flex": "1", "marginRight": "30px"}),
            html.Div([
                html.Div("Aux Outputs (−10.5 – +10.5 V)",
                         style={"fontSize": "0.80em","color":_MUTED,"fontWeight":"700",
                                "letterSpacing":"0.05em","marginBottom":"8px"}),
                *[_aux_out_row(ch) for ch in range(1, 5)],
            ], style={"flex": "1"}),
        ], style={"display": "flex", "flexWrap": "wrap"}),
    ], style=_CONTENT_CARD)

    _btn_primary = lambda label, id_: html.Button(label, id=id_, n_clicks=0, style={
        "padding": "8px 18px", "background": _BLUE, "color": "#fff",
        "border": "none", "borderRadius": "6px", "cursor": "pointer",
        "fontSize": "0.87em", "marginRight": "10px",
    })
    _btn_secondary = lambda label, id_: html.Button(label, id=id_, n_clicks=0, style={
        "padding": "8px 18px", "background": "#6c757d", "color": "#fff",
        "border": "none", "borderRadius": "6px", "cursor": "pointer",
        "fontSize": "0.87em", "marginRight": "10px",
    })
    _btn_danger = lambda label, id_: html.Button(label, id=id_, n_clicks=0, style={
        "padding": "8px 18px", "background": "#dc3545", "color": "#fff",
        "border": "none", "borderRadius": "6px", "cursor": "pointer",
        "fontSize": "0.87em", "marginRight": "10px",
    })

    _rec_content = html.Div([
        # Action bar
        html.Div([
            html.Div([
                _btn_primary("Record Snapshot", "btn-record-snapshot"),
                _btn_secondary("Clear All", "btn-clear-recordings"),
                _btn_primary("Download CSV", "btn-download-csv"),
            ], style={"display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "0"}),
            html.Span("", id="rec-status", style={**_STATUS, "marginLeft": "6px"}),
        ], style={"marginBottom": "16px"}),

        # Graph
        html.Div([
            html.Div([
                html.Label("Plot parameter:", style={"fontSize": "0.85em", "color": _MUTED,
                                                      "marginRight": "10px", "fontWeight": "600"}),
                dcc.Dropdown(id="graph-param-dd", options=GRAPH_PARAMS, value="R",
                             clearable=False, style={"width": "260px", "fontSize": "0.87em",
                                                     "display": "inline-block"}),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}),
            dcc.Graph(id="recordings-graph", style={"height": "260px"},
                      config={"displayModeBar": False}),
        ], style={**_CONTENT_CARD, "marginBottom": "14px", "padding": "14px 18px"}),

        # Table
        html.Div([
            html.Div("Recorded Data", style={**_PANEL_HDR, "marginBottom": "12px"}),
            dash_table.DataTable(
                id="recordings-table",
                data=[], columns=[],
                page_size=20,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": _BLUE_DARK, "color": "#fff",
                    "fontWeight": "700", "fontSize": "0.80em", "padding": "8px 10px",
                    "border": "none",
                },
                style_cell={
                    "fontFamily": "monospace", "fontSize": "0.80em",
                    "padding": "6px 10px", "border": f"1px solid {_BORDER}",
                    "backgroundColor": _SURFACE, "color": _TEXT,
                    "maxWidth": "160px", "overflow": "hidden", "textOverflow": "ellipsis",
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
                ],
                fixed_rows={"headers": True},
                style_as_list_view=False,
            ),
        ], style=_CONTENT_CARD),
    ])

    _cfg_content = html.Div([
        # Selection + actions
        html.Div([
            html.Div("Saved Configurations", style={**_PANEL_HDR, "marginBottom": "12px"}),
            html.Div([
                html.Div([
                    html.Label("Select configuration:", style={"fontSize": "0.82em",
                                                                "color": _MUTED, "marginBottom": "4px",
                                                                "display": "block"}),
                    dcc.Dropdown(id="config-dropdown", options=[], placeholder="Select a saved configuration…",
                                 clearable=True, style={"fontSize": "0.87em", "minWidth": "280px"}),
                ], style={"marginRight": "20px", "flex": "1", "maxWidth": "400px"}),
                html.Div([
                    _btn_primary("Apply to Amplifier", "btn-apply-config"),
                    html.Button("Edit in Editor ↓", id="btn-edit-config", n_clicks=0, style={
                        "padding": "8px 18px", "background": "#495057", "color": "#fff",
                        "border": "none", "borderRadius": "6px", "cursor": "pointer",
                        "fontSize": "0.87em", "marginRight": "10px",
                    }),
                    _btn_danger("Delete", "btn-delete-config"),
                ], style={"display": "flex", "alignItems": "flex-end", "flexWrap": "wrap",
                          "gap": "0 0", "paddingBottom": "2px"}),
            ], style={"display": "flex", "alignItems": "flex-end", "flexWrap": "wrap", "gap": "12px 0"}),
            html.Div("", id="cfg-action-status",
                     style={**_STATUS, "marginTop": "8px", "display": "block"}),
        ], style={**_CONTENT_CARD, "marginBottom": "14px"}),

        # Editor
        html.Div([
            html.Div("Configuration Editor", style={**_PANEL_HDR, "marginBottom": "14px"}),
            html.Div([
                html.Label("Configuration name *", style={"fontSize": "0.82em", "color": _MUTED,
                                                           "display": "block", "marginBottom": "4px"}),
                dcc.Input(id="cfg-name", type="text", placeholder="e.g. Baseline 1kHz",
                          debounce=False, style={**_NUM_WIDE, "width": "280px", "margin": "0",
                                                 "marginBottom": "16px"}),
            ]),
            html.Div("Parameters (leave blank to exclude from configuration):",
                     style={"fontSize": "0.82em", "color": _MUTED, "marginBottom": "10px",
                            "fontStyle": "italic"}),
            html.Div([
                _cfg_num("Frequency (Hz)  0.001–102000",        "cfg-frequency"),
                _cfg_num("Phase (°)  −360–+729.99",             "cfg-phase"),
            ], style={"display": "flex", "flexWrap": "wrap"}),
            html.Div([
                _cfg_num("Sine Amplitude (Vrms)  0.004–5.000",  "cfg-sine-amp"),
                _cfg_num("Detection Harmonic  1–19999",         "cfg-harmonic"),
            ], style={"display": "flex", "flexWrap": "wrap"}),
            html.Div([
                _cfg_dd("Reference Source",  "cfg-ref-src",  REF_SRC_OPTS),
                _cfg_dd("Reference Trigger", "cfg-ref-trig", REF_TRIG_OPTS),
            ], style={"display": "flex", "flexWrap": "wrap"}),
            html.Div([
                _cfg_dd("Sensitivity",       "cfg-sensitivity",  SENS_OPTS),
                _cfg_dd("Reserve Mode",      "cfg-reserve",      RESERVE_OPTS),
            ], style={"display": "flex", "flexWrap": "wrap"}),
            html.Div([
                _cfg_dd("Time Constant",     "cfg-time-constant",TC_OPTS),
                _cfg_dd("Filter Slope",      "cfg-filter-slope", SLOPE_OPTS),
            ], style={"display": "flex", "flexWrap": "wrap"}),
            html.Div([
                _cfg_dd("Sync Filter",       "cfg-sync-filter",  SYNC_OPTS),
                _cfg_dd("Input Config",      "cfg-input-cfg",    INPUT_CFG_OPTS),
            ], style={"display": "flex", "flexWrap": "wrap"}),
            html.Div([
                _cfg_dd("Input Shield GND",  "cfg-input-gnd",    INPUT_GND_OPTS),
                _cfg_dd("Input Coupling",    "cfg-input-cpl",    INPUT_CPL_OPTS),
            ], style={"display": "flex", "flexWrap": "wrap"}),
            html.Div([
                _cfg_dd("Line Notch Filter", "cfg-notch",        NOTCH_OPTS),
                html.Div(style={"flex": "1", "minWidth": "200px", "marginRight": "14px"}),
            ], style={"display": "flex", "flexWrap": "wrap"}),
            html.Div([
                _btn_primary("Save Configuration", "btn-save-config"),
                _btn_secondary("Clear Editor", "btn-clear-editor"),
            ], style={"marginTop": "6px", "display": "flex"}),
            html.Div("", id="cfg-editor-status",
                     style={**_STATUS, "marginTop": "8px", "display": "block"}),
        ], style=_CONTENT_CARD),
    ])

    # ── Display channels strip (horizontal, below tab content) ────────────────
    def _dd_labeled(label, **dd_kwargs):
        return html.Div([
            html.Label(label, style={"fontSize": "0.74em", "color": _MUTED,
                                     "display": "block", "marginBottom": "2px"}),
            dcc.Dropdown(clearable=False, style={"fontSize": "0.85em"}, **dd_kwargs),
        ], style={"flex": "1", "marginRight": "8px", "minWidth": "110px"})

    _display_strip = html.Div([
        html.Div("Display Channels", style={**_PANEL_HDR, "marginBottom": "14px"}),
        html.Div([
            # CH1
            html.Div([
                html.Div("Channel 1", style={"fontSize": "0.77em", "fontWeight": "700",
                                             "color": _MUTED, "marginBottom": "8px"}),
                html.Div([
                    _dd_labeled("Parameter", id="ddef1-param", options=DDEF_PARAM_OPTS, value=0),
                    _dd_labeled("Ratio",     id="ddef1-ratio", options=DDEF_RATIO_OPTS, value=0),
                    _dd_labeled("Output src",id="fpop1-src",   options=FPOP_CH1_OPTS,   value=0),
                    html.Div([
                        html.Label(" ", style={"fontSize": "0.74em", "display": "block", "marginBottom": "2px"}),
                        html.Button("Apply", id="btn-set-ddef1", n_clicks=0, style=_BTN_SET),
                    ]),
                ], style={"display": "flex", "alignItems": "flex-end", "marginBottom": "12px"}),
                html.Div(html.Span("—", id="display-ch1-val", style={
                    "fontFamily": "monospace", "fontSize": "2.6em",
                    "color": _BLUE, "fontWeight": "700",
                }), style={
                    "background": _BLUE_LIGHT, "border": f"1px solid {_BORDER}",
                    "borderRadius": "8px", "padding": "14px 20px", "textAlign": "center",
                }),
            ], style={"flex": "1", "marginRight": "24px"}),
            # CH2
            html.Div([
                html.Div("Channel 2", style={"fontSize": "0.77em", "fontWeight": "700",
                                             "color": _MUTED, "marginBottom": "8px"}),
                html.Div([
                    _dd_labeled("Parameter", id="ddef2-param", options=DDEF_PARAM_OPTS, value=1),
                    _dd_labeled("Ratio",     id="ddef2-ratio", options=DDEF_RATIO_OPTS, value=0),
                    _dd_labeled("Output src",id="fpop2-src",   options=FPOP_CH2_OPTS,   value=0),
                    html.Div([
                        html.Label(" ", style={"fontSize": "0.74em", "display": "block", "marginBottom": "2px"}),
                        html.Button("Apply", id="btn-set-ddef2", n_clicks=0, style=_BTN_SET),
                    ]),
                ], style={"display": "flex", "alignItems": "flex-end", "marginBottom": "12px"}),
                html.Div(html.Span("—", id="display-ch2-val", style={
                    "fontFamily": "monospace", "fontSize": "2.6em",
                    "color": _BLUE, "fontWeight": "700",
                }), style={
                    "background": _BLUE_LIGHT, "border": f"1px solid {_BORDER}",
                    "borderRadius": "8px", "padding": "14px 20px", "textAlign": "center",
                }),
            ], style={"flex": "1"}),
        ], style={"display": "flex"}),
        html.Div([
            html.Span("↻ auto-refresh 500 ms", style={"fontSize": "0.72em", "color": _MUTED}),
            html.Span("", id="status-ddef", style={**_STATUS, "marginLeft": "16px"}),
        ], style={"marginTop": "10px", "display": "flex", "alignItems": "center"}),
    ], style={**_CONTENT_CARD, "marginTop": "14px"})

    # ── Layout ────────────────────────────────────────────────────────────────
    app.layout = html.Div([

        dcc.Store(id="active-tab", data="ref"),
        dcc.Store(id="recordings-store", data=[]),
        dcc.Store(id="config-store", storage_type="local", data={}),
        dcc.Store(id="pending-quick-cfg", data=None),
        dcc.Download(id="download-csv"),
        dcc.Interval(id="log-interval",      interval=2000, n_intervals=0),
        dcc.Interval(id="display-interval",  interval=500,  n_intervals=0),
        dcc.Interval(id="periodic-interval", interval=5000, n_intervals=0, disabled=True),
        dcc.ConfirmDialog(id="confirm-quick-cfg", message=""),

        # Header
        html.Div([
            html.Div([
                html.H1("SR830 Lock-In Amplifier",
                        style={"margin": "0", "color": "#fff", "fontSize": "1.25em",
                               "fontWeight": "700", "letterSpacing": "0.02em"}),
                html.Div("Remote Control Interface",
                         style={"color": "#acd4f0", "fontSize": "0.82em", "marginTop": "2px"}),
            ]),
            html.Div("● Connected",
                     style={"color": "#a8e6cf", "fontSize": "0.80em",
                            "fontFamily": "monospace", "alignSelf": "flex-end"}),
        ], style={
            "background": f"linear-gradient(135deg, {_BLUE} 0%, {_BLUE_DARK} 100%)",
            "padding": "12px 22px",
            "display": "flex", "justifyContent": "space-between", "alignItems": "flex-end",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.25)",
        }),

        # Nav bar
        html.Div([
            *[html.Button(_TAB_LABELS[t], id=f"nav-btn-{t}", n_clicks=0,
                          style=_NAV_BTN_ACT if t == "ref" else _NAV_BTN)
              for t in ["ref", "gain", "input", "aux", "rec"]],
            html.Div(style={"flex": "1"}),
            html.Div([
                dcc.Dropdown(
                    id="nav-quick-cfg",
                    options=[],
                    placeholder=" Select Configuration",
                    clearable=True,
                    style={
                        "width": "230px", "fontSize": "0.82em",
                        "background": _BLUE_MID, "color": "#fff",
                    },
                ),
            ], style={"display": "flex", "alignItems": "center", "padding": "0 10px"}),
            html.Button(_TAB_LABELS["cfg"], id="nav-btn-cfg", n_clicks=0,
                        style={**_NAV_BTN,
                               "borderLeft": f"1px solid {_BLUE_MID}",
                               "color": "#a8c8e8"}),
        ], style={
            "background": _BLUE_DARK,
            "display": "flex", "alignItems": "stretch",
            "padding": "0 18px",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.2)",
            "flexShrink": "0",
        }),

        # Body: sidebar + content
        html.Div([

            # Left sidebar
            html.Div([
                # Measurements
                html.Div([
                    html.H4("Measurements", style=_PANEL_HDR),
                    _meas_row("X", "out-x"),
                    _meas_row("Y", "out-y"),
                    _meas_row("R", "out-r"),
                    _meas_row("θ", "out-theta"),
                    html.Button("Read  X, Y, R, θ", id="btn-read-all", n_clicks=0, style={
                        "width": "100%", "padding": "8px 0", "marginTop": "10px",
                        "background": _BLUE, "color": "#fff", "border": "none",
                        "borderRadius": "6px", "cursor": "pointer",
                        "fontSize": "0.85em", "fontWeight": "600",
                    }),
                    html.Button("Read All Parameters", id="btn-read-all-params", n_clicks=0, style={
                        "width": "100%", "padding": "8px 0", "marginTop": "6px",
                        "background": "#17a2b8", "color": "#fff", "border": "none",
                        "borderRadius": "6px", "cursor": "pointer",
                        "fontSize": "0.85em", "fontWeight": "600",
                    }),
                ], style=_PANEL),

                # Auto Functions
                html.Div([
                    html.H4("Auto Functions", style=_PANEL_HDR),
                    html.Button("Auto Gain",    id="btn-auto-gain",    n_clicks=0, style=_SIDEBAR_BTN),
                    html.Button("Auto Reserve", id="btn-auto-reserve", n_clicks=0, style=_SIDEBAR_BTN),
                    html.Button("Auto Phase",   id="btn-auto-phase",   n_clicks=0, style=_SIDEBAR_BTN),
                    html.Div("", id="status-auto",
                             style={"fontFamily": "monospace", "fontSize": "0.79em",
                                    "marginTop": "4px", "minHeight": "18px"}),
                ], style=_PANEL),

                # Periodic Measurement
                html.Div([
                    html.H4("Periodic Measurement", style=_PANEL_HDR),
                    html.Div([
                        html.Span("Interval (s):", style={"fontSize": "0.81em", "color": _MUTED}),
                        dcc.Input(id="in-periodic-interval", type="number", value=5, min=1, max=3600,
                                  debounce=False, style={
                                      "width": "65px", "marginLeft": "6px", "padding": "4px 6px",
                                      "border": f"1px solid {_BORDER}", "borderRadius": "4px",
                                      "fontSize": "0.83em",
                                  }),
                    ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px"}),
                    html.Button("▶ Start", id="btn-periodic-toggle", n_clicks=0, style=_SIDEBAR_BTN),
                    html.Div("", id="status-periodic",
                             style={"fontFamily": "monospace", "fontSize": "0.77em",
                                    "marginTop": "4px", "minHeight": "16px"}),
                ], style=_PANEL),

            ], style={
                "width": "210px", "minWidth": "210px", "flexShrink": "0",
                "paddingTop": "16px", "paddingLeft": "4px",
            }),

            # Right content area
            html.Div([
                html.Div(_ref_content,   id="content-ref",   style={"display": "block"}),
                html.Div(_gain_content,  id="content-gain",  style={"display": "none"}),
                html.Div(_input_content, id="content-input", style={"display": "none"}),
                html.Div(_aux_content,   id="content-aux",   style={"display": "none"}),
                html.Div(_rec_content,   id="content-rec",   style={"display": "none"}),
                html.Div(_cfg_content,   id="content-cfg",   style={"display": "none"}),
                _display_strip,
            ], style={"flex": "1", "minWidth": "0", "padding": "16px 12px 16px 10px"}),

        ], style={
            "display": "flex", "gap": "0 10px",
            "padding": "0 18px", "flex": "1", "alignItems": "flex-start",
        }),

        # Log panel (bottom, full width)
        html.Div([
            html.Div([
                html.Span("Log", style={
                    "fontSize": "0.73em", "fontWeight": "800", "color": "#8b949e",
                    "letterSpacing": "0.12em", "textTransform": "uppercase",
                }),
                html.Button("Clear", id="btn-clear-log", n_clicks=0, style={
                    "padding": "2px 9px", "fontSize": "0.71em",
                    "background": "#21262d", "color": "#8b949e",
                    "border": "1px solid #30363d", "borderRadius": "4px", "cursor": "pointer",
                }),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "alignItems": "center", "marginBottom": "6px",
                      "borderBottom": "1px solid #30363d", "paddingBottom": "6px"}),
            html.Div(
                id="log-display",
                children=[html.Div("Waiting for log entries…",
                                   style={"color": "#484f58", "fontSize": "0.73em",
                                          "fontFamily": "monospace", "whiteSpace": "nowrap"})],
                style={
                    "height": "130px", "minHeight": "60px", "overflowY": "auto", "overflowX": "auto",
                    "background": "#0d1117", "borderRadius": "6px", "padding": "6px 10px",
                    "resize": "vertical",
                },
            ),
        ], style={
            "background": "#161b22", "border": "1px solid #30363d",
            "padding": "10px 16px", "margin": "0",
            "flexShrink": "0",
        }),

    ], style={
        "background": _BG, "minHeight": "100vh",
        "display": "flex", "flexDirection": "column",
        "fontFamily": "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    })

    # ════════════════════════════════════════════════════════════════════════
    #  CALLBACKS
    # ════════════════════════════════════════════════════════════════════════

    # ── Navigation ────────────────────────────────────────────────────────────
    @app.callback(
        Output("active-tab", "data"),
        *[Output(f"nav-btn-{t}", "style") for t in _TABS],
        *[Input(f"nav-btn-{t}", "n_clicks") for t in _TABS],
        State("active-tab", "data"),
        prevent_initial_call=False,
    )
    def cb_nav(*args):
        n_tabs = len(_TABS)
        clicks = args[:n_tabs]
        current = args[n_tabs]
        ctx = dash.callback_context
        if ctx.triggered and ctx.triggered[0]["prop_id"] != ".":
            active = ctx.triggered[0]["prop_id"].split(".")[0].replace("nav-btn-", "")
        else:
            active = current or "ref"
        cfg_base = {**_NAV_BTN, "borderLeft": f"1px solid {_BLUE_MID}", "color": "#a8c8e8"}
        cfg_act  = {**_NAV_BTN_ACT, "borderLeft": f"1px solid {_BLUE_MID}"}
        styles = []
        for t in _TABS:
            if t == "cfg":
                styles.append(cfg_act if t == active else cfg_base)
            else:
                styles.append(_NAV_BTN_ACT if t == active else _NAV_BTN)
        return (active, *styles)

    @app.callback(
        *[Output(f"content-{t}", "style") for t in _TABS],
        Input("active-tab", "data"),
    )
    def cb_visibility(active):
        return [{"display": "block"} if t == active else {"display": "none"} for t in _TABS]

    # ── Log ───────────────────────────────────────────────────────────────────
    @app.callback(
        Output("log-display", "children"),
        Input("log-interval", "n_intervals"),
        Input("btn-clear-log", "n_clicks"),
        prevent_initial_call=False,
    )
    def cb_log(_, __):
        ctx = dash.callback_context
        if ctx.triggered and ctx.triggered[0]["prop_id"] == "btn-clear-log.n_clicks":
            _log_handler.clear()
            return [html.Div("Log cleared.", style={"color": "#484f58", "fontSize": "0.73em",
                                                    "fontFamily": "monospace", "whiteSpace": "nowrap"})]
        recs = _log_handler.get_records()
        if not recs:
            return [html.Div("Waiting for log entries…",
                             style={"color": "#484f58", "fontSize": "0.73em",
                                    "fontFamily": "monospace", "whiteSpace": "nowrap"})]
        return [_log_entry(lvl, msg) for lvl, msg in reversed(recs)]

    # ── Read X, Y, R, θ ───────────────────────────────────────────────────────
    @app.callback(
        Output("out-x",     "children"),
        Output("out-y",     "children"),
        Output("out-r",     "children"),
        Output("out-theta", "children"),
        Input("btn-read-all", "n_clicks"),
        prevent_initial_call=True,
    )
    def cb_read_xyrtheta(_):
        try:
            x, y, r, theta = amp.read_parameters()
            return f"{x:.6f} V", f"{y:.6f} V", f"{r:.6f} V", f"{theta:.4f}°"
        except Exception as e:
            m = f"✗ {e}"; return m, m, m, m

    # ── Read All Parameters ───────────────────────────────────────────────────
    @app.callback(
        Output("out-x",            "children", allow_duplicate=True),
        Output("out-y",            "children", allow_duplicate=True),
        Output("out-r",            "children", allow_duplicate=True),
        Output("out-theta",        "children", allow_duplicate=True),
        Output("out-frequency",    "children", allow_duplicate=True),
        Output("out-phase",        "children", allow_duplicate=True),
        Output("out-sine-amp",     "children", allow_duplicate=True),
        Output("out-ref-src",      "children", allow_duplicate=True),
        Output("out-ref-trig",     "children", allow_duplicate=True),
        Output("out-harmonic",     "children", allow_duplicate=True),
        Output("out-sensitivity",  "children", allow_duplicate=True),
        Output("out-reserve",      "children", allow_duplicate=True),
        Output("out-time-constant","children", allow_duplicate=True),
        Output("out-filter-slope", "children", allow_duplicate=True),
        Output("out-sync-filter",  "children", allow_duplicate=True),
        Output("out-input-cfg",    "children", allow_duplicate=True),
        Output("out-input-gnd",    "children", allow_duplicate=True),
        Output("out-input-cpl",    "children", allow_duplicate=True),
        Output("out-notch",        "children", allow_duplicate=True),
        Output("out-aux-in-1",     "children", allow_duplicate=True),
        Output("out-aux-in-2",     "children", allow_duplicate=True),
        Output("out-aux-in-3",     "children", allow_duplicate=True),
        Output("out-aux-in-4",     "children", allow_duplicate=True),
        Input("btn-read-all-params", "n_clicks"),
        prevent_initial_call=True,
    )
    def cb_read_all_params(_):
        try:
            p = amp.read_all_params()
        except Exception as e:
            m = f"✗ {e}"
            return (m,) * 23

        def _get(key, fmt="{}"):
            return fmt.format(p[key]) if key in p else "✗"

        def _lbl(key, lmap):
            i = p.get(key)
            return lmap.get(i, "✗") if i is not None else "✗"

        return (
            _get("X",     "{:.6f} V"),
            _get("Y",     "{:.6f} V"),
            _get("R",     "{:.6f} V"),
            _get("theta", "{:.4f}°"),
            _get("frequency", "{:.6f} Hz"),
            _get("phase",     "{:.2f}°"),
            _get("sine_amp",  "{:.4f} Vrms"),
            _lbl("ref_src",  _SRC_LABELS),
            _lbl("ref_trig", _TRIG_LABELS),
            _get("harmonic"),
            _sl(p["sensitivity"])   if "sensitivity"   in p else "✗",
            _rl(p["reserve"])       if "reserve"       in p else "✗",
            _tl(p["time_constant"]) if "time_constant" in p else "✗",
            _fl(p["filter_slope"])  if "filter_slope"  in p else "✗",
            _lbl("sync_filter", _SYNC_LABELS),
            _lbl("input_cfg",   _CFG_LABELS),
            _lbl("input_gnd",   _GND_LABELS),
            _lbl("input_cpl",   _CPL_LABELS),
            _lbl("notch",       _NOTCH_LABELS),
            _get("aux_in_1", "{:.4f} V"),
            _get("aux_in_2", "{:.4f} V"),
            _get("aux_in_3", "{:.4f} V"),
            _get("aux_in_4", "{:.4f} V"),
        )

    # ── Auto Functions ────────────────────────────────────────────────────────
    @app.callback(
        Output("status-auto", "children"),
        Input("btn-auto-gain",    "n_clicks"),
        Input("btn-auto-reserve", "n_clicks"),
        Input("btn-auto-phase",   "n_clicks"),
        prevent_initial_call=True,
    )
    def cb_auto(_, __, ___):
        ctx = dash.callback_context
        t = ctx.triggered[0]["prop_id"].split(".")[0]
        try:
            if t == "btn-auto-gain":    amp.auto_gain();    return _ok("✓ Auto Gain")
            if t == "btn-auto-reserve": amp.auto_reserve(); return _ok("✓ Auto Reserve")
            if t == "btn-auto-phase":   amp.auto_phase();   return _ok("✓ Auto Phase")
        except Exception as e: return _err(f"✗ {e}")
        return ""

    # ── Frequency ─────────────────────────────────────────────────────────────
    @app.callback(Output("out-frequency","children"), Input("btn-read-frequency","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_freq(_): return f"{amp.frequency():.6f} Hz"

    @app.callback(Output("status-frequency","children"), Output("in-frequency","style"),
                  Input("btn-set-frequency","n_clicks"), State("in-frequency","value"),
                  prevent_initial_call=True)
    def cb_st_freq(_, v):
        if v is None: return _warn("⚠ Enter a value first."), _NUM_WIDE
        try:
            amp.set_frequency(float(v)); return _ok(f"✓ {float(v):.4f} Hz"), _NUM_WIDE
        except ValueError as e: return _err(f"✗ {e}"), _NUM_WIDE_INVALID

    # ── Phase ─────────────────────────────────────────────────────────────────
    @app.callback(Output("out-phase","children"), Input("btn-read-phase","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_phase(_): return f"{amp.phase():.2f}°"

    @app.callback(Output("status-phase","children"), Output("in-phase","style"),
                  Input("btn-set-phase","n_clicks"), State("in-phase","value"),
                  prevent_initial_call=True)
    def cb_st_phase(_, v):
        if v is None: return _warn("⚠ Enter a value first."), _NUM_WIDE
        try:
            amp.set_phase(float(v)); return _ok(f"✓ {float(v):.2f}°"), _NUM_WIDE
        except ValueError as e: return _err(f"✗ {e}"), _NUM_WIDE_INVALID

    # ── Sine Amplitude ─────────────────────────────────────────────────────────
    @app.callback(Output("out-sine-amp","children"), Input("btn-read-sine-amp","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_sine(_): return f"{amp.sine_amplitude():.4f} Vrms"

    @app.callback(Output("status-sine-amp","children"), Output("in-sine-amp","style"),
                  Input("btn-set-sine-amp","n_clicks"), State("in-sine-amp","value"),
                  prevent_initial_call=True)
    def cb_st_sine(_, v):
        if v is None: return _warn("⚠ Enter a value first."), _NUM_WIDE
        try:
            amp.set_sine_amplitude(float(v)); return _ok(f"✓ {float(v):.4f} Vrms"), _NUM_WIDE
        except ValueError as e: return _err(f"✗ {e}"), _NUM_WIDE_INVALID

    # ── Reference Source ──────────────────────────────────────────────────────
    @app.callback(Output("out-ref-src","children"), Input("btn-read-ref-src","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_src(_):
        i = amp.reference_source(); return _SRC_LABELS[i]

    @app.callback(Output("status-ref-src","children"), Input("btn-set-ref-src","n_clicks"),
                  State("in-ref-src","value"), prevent_initial_call=True)
    def cb_st_src(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: amp.set_reference_source(int(v)); return _ok(f"✓ {_SRC_LABELS[int(v)]}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Reference Trigger ─────────────────────────────────────────────────────
    @app.callback(Output("out-ref-trig","children"), Input("btn-read-ref-trig","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_trig(_):
        i = amp.reference_trigger(); return _TRIG_LABELS[i]

    @app.callback(Output("status-ref-trig","children"), Input("btn-set-ref-trig","n_clicks"),
                  State("in-ref-trig","value"), prevent_initial_call=True)
    def cb_st_trig(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: amp.set_reference_trigger(int(v)); return _ok(f"✓ {_TRIG_LABELS[int(v)]}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Detection Harmonic ────────────────────────────────────────────────────
    @app.callback(Output("out-harmonic","children"), Input("btn-read-harmonic","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_harm(_): return f"{amp.detection_harmonic()}"

    @app.callback(Output("status-harmonic","children"), Output("in-harmonic","style"),
                  Input("btn-set-harmonic","n_clicks"), State("in-harmonic","value"),
                  prevent_initial_call=True)
    def cb_st_harm(_, v):
        if v is None: return _warn("⚠ Enter a value first."), _NUM_WIDE
        try:
            i = int(v)
            if not 1 <= i <= 19999: raise ValueError(f"Harmonic {i} out of range (1–19999).")
            amp.set_detection_harmonic(i); return _ok(f"✓ {i}"), _NUM_WIDE
        except ValueError as e: return _err(f"✗ {e}"), _NUM_WIDE_INVALID

    # ── Sensitivity ───────────────────────────────────────────────────────────
    @app.callback(Output("out-sensitivity","children"), Input("btn-read-sensitivity","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_sens(_):
        i = amp.sensitivity(); return _sl(i)

    @app.callback(Output("status-sensitivity","children"), Input("btn-set-sensitivity","n_clicks"),
                  State("in-sensitivity","value"), prevent_initial_call=True)
    def cb_st_sens(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: i=int(v); amp.set_sensitivity(i); return _ok(f"✓ {_sl(i)}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Reserve Mode ──────────────────────────────────────────────────────────
    @app.callback(Output("out-reserve","children"), Input("btn-read-reserve","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_res(_):
        i = amp.reserve_mode(); return _rl(i)

    @app.callback(Output("status-reserve","children"), Input("btn-set-reserve","n_clicks"),
                  State("in-reserve","value"), prevent_initial_call=True)
    def cb_st_res(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: i=int(v); amp.set_reserve_mode(i); return _ok(f"✓ {_rl(i)}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Time Constant ─────────────────────────────────────────────────────────
    @app.callback(Output("out-time-constant","children"), Input("btn-read-time-constant","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_tc(_):
        i = amp.time_constant(); return _tl(i)

    @app.callback(Output("status-time-constant","children"), Input("btn-set-time-constant","n_clicks"),
                  State("in-time-constant","value"), prevent_initial_call=True)
    def cb_st_tc(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: i=int(v); amp.set_time_constant(i); return _ok(f"✓ {_tl(i)}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Filter Slope ──────────────────────────────────────────────────────────
    @app.callback(Output("out-filter-slope","children"), Input("btn-read-filter-slope","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_fs(_):
        i = amp.low_pass_filter_slope(); return _fl(i)

    @app.callback(Output("status-filter-slope","children"), Input("btn-set-filter-slope","n_clicks"),
                  State("in-filter-slope","value"), prevent_initial_call=True)
    def cb_st_fs(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: i=int(v); amp.set_low_pass_filter_slope(i); return _ok(f"✓ {_fl(i)}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Synchronous Filter ────────────────────────────────────────────────────
    @app.callback(Output("out-sync-filter","children"), Input("btn-read-sync-filter","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_syn(_):
        i = amp.synchronous_filter(); return _SYNC_LABELS[i]

    @app.callback(Output("status-sync-filter","children"), Input("btn-set-sync-filter","n_clicks"),
                  State("in-sync-filter","value"), prevent_initial_call=True)
    def cb_st_syn(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: i=int(v); amp.set_synchronous_filter(i); return _ok(f"✓ {_SYNC_LABELS[i]}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Input Configuration ───────────────────────────────────────────────────
    @app.callback(Output("out-input-cfg","children"), Input("btn-read-input-cfg","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_icfg(_):
        i = amp.input_configuration(); return _CFG_LABELS[i]

    @app.callback(Output("status-input-cfg","children"), Input("btn-set-input-cfg","n_clicks"),
                  State("in-input-cfg","value"), prevent_initial_call=True)
    def cb_st_icfg(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: amp.set_input_configuration(int(v)); return _ok(f"✓ {_CFG_LABELS[int(v)]}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Input Shield Grounding ────────────────────────────────────────────────
    @app.callback(Output("out-input-gnd","children"), Input("btn-read-input-gnd","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_gnd(_):
        i = amp.input_shield_grounding(); return _GND_LABELS[i]

    @app.callback(Output("status-input-gnd","children"), Input("btn-set-input-gnd","n_clicks"),
                  State("in-input-gnd","value"), prevent_initial_call=True)
    def cb_st_gnd(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: amp.set_input_shield_grounding(int(v)); return _ok(f"✓ {_GND_LABELS[int(v)]}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Input Coupling ────────────────────────────────────────────────────────
    @app.callback(Output("out-input-cpl","children"), Input("btn-read-input-cpl","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_cpl(_):
        i = amp.input_coupling(); return _CPL_LABELS[i]

    @app.callback(Output("status-input-cpl","children"), Input("btn-set-input-cpl","n_clicks"),
                  State("in-input-cpl","value"), prevent_initial_call=True)
    def cb_st_cpl(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: amp.set_input_coupling(int(v)); return _ok(f"✓ {_CPL_LABELS[int(v)]}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Line Notch Filter ─────────────────────────────────────────────────────
    @app.callback(Output("out-notch","children"), Input("btn-read-notch","n_clicks"),
                  prevent_initial_call=True)
    def cb_rd_notch(_):
        i = amp.input_line_notch_filter(); return _NOTCH_LABELS[i]

    @app.callback(Output("status-notch","children"), Input("btn-set-notch","n_clicks"),
                  State("in-notch","value"), prevent_initial_call=True)
    def cb_st_notch(_, v):
        if v is None: return _warn("⚠ Select a value first.")
        try: amp.set_input_line_notch_filter(int(v)); return _ok(f"✓ {_NOTCH_LABELS[int(v)]}")
        except ValueError as e: return _err(f"✗ {e}")

    # ── Aux Inputs ────────────────────────────────────────────────────────────
    for _ch in range(1, 5):
        def _make_aux_in(ch):
            @app.callback(Output(f"out-aux-in-{ch}","children"),
                          Input(f"btn-read-aux-in-{ch}","n_clicks"), prevent_initial_call=True)
            def _cb(_, _ch=ch):
                try:
                    return f"{amp.aux_input(_ch):.4f} V"
                except Exception as e:
                    logger.warning(f"Aux input {_ch} read failed: {e}")
                    return f"✗ {e}"
        _make_aux_in(_ch)

    # ── Aux Outputs ───────────────────────────────────────────────────────────
    for _ch in range(1, 5):
        def _make_aux_out(ch):
            @app.callback(Output(f"status-aux-out-{ch}","children"),
                          Output(f"in-aux-out-{ch}","style"),
                          Input(f"btn-set-aux-out-{ch}","n_clicks"),
                          State(f"in-aux-out-{ch}","value"), prevent_initial_call=True)
            def _cb(_, v, _ch=ch):
                base = {**_NUM_WIDE, "width": "200px"}
                inv  = {**base, "border": f"2px solid {_RED}", "boxShadow": f"0 0 0 3px rgba(198,40,40,0.15)"}
                if v is None: return _warn("⚠ Enter a voltage first."), base
                try: amp.set_aux_output(_ch, float(v)); return _ok(f"✓ {float(v):.4f} V"), base
                except ValueError as e: return _err(f"✗ {e}"), inv
        _make_aux_out(_ch)

    # ── Recordings: snapshot + clear ──────────────────────────────────────────
    @app.callback(
        Output("recordings-store", "data"),
        Output("rec-status", "children"),
        Input("btn-record-snapshot",  "n_clicks"),
        Input("btn-clear-recordings", "n_clicks"),
        State("recordings-store", "data"),
        prevent_initial_call=True,
    )
    def cb_recordings(n_rec, n_clr, records):
        ctx = dash.callback_context
        if ctx.triggered[0]["prop_id"] == "btn-clear-recordings.n_clicks":
            return [], _ok("Cleared.")
        rec = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}
        try:
            params = amp.read_all_params()
            # Apply scientific rounding to measurements
            if "X"     in params: params["X"]     = round(params["X"],     8)
            if "Y"     in params: params["Y"]     = round(params["Y"],     8)
            if "R"     in params: params["R"]     = round(params["R"],     8)
            if "theta" in params: params["theta"] = round(params["theta"], 5)
            rec.update(params)
        except Exception as e:
            logger.warning(f"Snapshot read_all_params failed: {e}")
        records = list(records or [])
        records.append(rec)
        n = len(records)
        logger.info(f"Snapshot #{n} recorded — {len(rec)-1} parameters captured")
        return records, _ok(f"✓ Snapshot #{n} recorded")

    # ── Recordings: table ─────────────────────────────────────────────────────
    @app.callback(
        Output("recordings-table", "data"),
        Output("recordings-table", "columns"),
        Input("recordings-store", "data"),
    )
    def cb_table(records):
        if not records: return [], []
        all_keys = [k for k in _COLS if k in records[0]] + \
                   [k for k in records[0] if k not in _COLS]
        cols = [{"name": c, "id": c} for c in all_keys]
        return records, cols

    # ── Recordings: graph ─────────────────────────────────────────────────────
    @app.callback(
        Output("recordings-graph", "figure"),
        Input("recordings-store", "data"),
        Input("graph-param-dd", "value"),
    )
    def cb_graph(records, param):
        fig = go.Figure()
        fig.update_layout(
            margin=dict(l=44, r=12, t=10, b=44),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#f8f9fa",
            xaxis=dict(showgrid=True, gridcolor=_BORDER, title="Timestamp",
                       tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor=_BORDER, title=param or "",
                       tickfont=dict(size=10)),
            font=dict(family="'Segoe UI', Arial, sans-serif", size=11),
            hovermode="x unified",
        )
        if not records or not param: return fig
        pts = [(r["timestamp"], r[param]) for r in records if param in r]
        if not pts: return fig
        xs, ys = zip(*pts)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            line=dict(color=_BLUE, width=2),
            marker=dict(size=6, color=_BLUE),
            hovertemplate="%{x}<br>%{y:.6g}<extra></extra>",
        ))
        return fig

    # ── Recordings: CSV download ──────────────────────────────────────────────
    @app.callback(
        Output("download-csv", "data"),
        Input("btn-download-csv", "n_clicks"),
        State("recordings-store", "data"),
        prevent_initial_call=True,
    )
    def cb_download(_, records):
        if not records: return None
        buf = io.StringIO()
        all_keys = list(dict.fromkeys(k for r in records for k in r))
        w = csv.DictWriter(buf, fieldnames=all_keys, extrasaction="ignore")
        w.writeheader(); w.writerows(records)
        return dict(content=buf.getvalue(), filename="sr830_recordings.csv")

    # ── Configurations: dropdown options from store ───────────────────────────
    @app.callback(
        Output("config-dropdown", "options"),
        Output("nav-quick-cfg",   "options"),
        Input("config-store", "data"),
    )
    def cb_cfg_opts(cfgs):
        opts = [{"label": n, "value": n} for n in (cfgs or {}).keys()]
        return opts, opts

    # ── Configurations: save + delete (combined, both write config-store) ─────
    @app.callback(
        Output("config-store",      "data"),
        Output("cfg-editor-status", "children"),
        Output("cfg-action-status", "children"),
        Input("btn-save-config",   "n_clicks"),
        Input("btn-delete-config", "n_clicks"),
        State("cfg-name",          "value"),
        State("cfg-frequency",     "value"), State("cfg-phase",        "value"),
        State("cfg-sine-amp",      "value"), State("cfg-harmonic",     "value"),
        State("cfg-ref-src",       "value"), State("cfg-ref-trig",     "value"),
        State("cfg-sensitivity",   "value"), State("cfg-reserve",      "value"),
        State("cfg-time-constant", "value"), State("cfg-filter-slope", "value"),
        State("cfg-sync-filter",   "value"), State("cfg-input-cfg",    "value"),
        State("cfg-input-gnd",     "value"), State("cfg-input-cpl",    "value"),
        State("cfg-notch",         "value"),
        State("config-dropdown",   "value"),
        State("config-store",      "data"),
        prevent_initial_call=True,
    )
    def cb_cfg_write(n_save, n_del, name,
                     freq, phase, sine, harm, rsrc, rtrig,
                     sens, res, tc, fslope, sync,
                     icfg, ignd, icpl, notch,
                     sel_name, cfgs):
        ctx = dash.callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0]
        cfgs = dict(cfgs or {})

        if triggered == "btn-save-config":
            if not name or not name.strip():
                return cfgs, _warn("⚠ Enter a configuration name."), ""
            cfg = {}
            for k, v in [("frequency",freq),("phase",phase),("sine_amp",sine),
                         ("harmonic",harm),("ref_src",rsrc),("ref_trig",rtrig),
                         ("sensitivity",sens),("reserve",res),("time_constant",tc),
                         ("filter_slope",fslope),("sync_filter",sync),
                         ("input_cfg",icfg),("input_gnd",ignd),("input_cpl",icpl),
                         ("notch",notch)]:
                if v is not None: cfg[k] = v
            cfgs[name.strip()] = cfg
            logger.info(f"Configuration '{name.strip()}' saved with {len(cfg)} parameters.")
            return cfgs, _ok(f"✓ Saved '{name.strip()}'"), ""

        if triggered == "btn-delete-config":
            if not sel_name or sel_name not in cfgs:
                return cfgs, "", _warn("⚠ Select a configuration to delete.")
            del cfgs[sel_name]
            return cfgs, "", _ok(f"✓ Deleted '{sel_name}'")

        return cfgs, "", ""

    # ── Configurations: apply to amplifier ───────────────────────────────────
    @app.callback(
        Output("cfg-action-status","children",allow_duplicate=True),
        Input("btn-apply-config","n_clicks"),
        State("config-dropdown","value"),
        State("config-store","data"),
        prevent_initial_call=True,
    )
    def cb_cfg_apply(_, name, cfgs):
        if not name or name not in (cfgs or {}):
            return _warn("⚠ Select a configuration first.")
        c = cfgs[name]; errs = []
        _setters = [
            ("frequency",    lambda v: amp.set_frequency(float(v))),
            ("phase",        lambda v: amp.set_phase(float(v))),
            ("sine_amp",     lambda v: amp.set_sine_amplitude(float(v))),
            ("harmonic",     lambda v: amp.set_detection_harmonic(int(v))),
            ("ref_src",      lambda v: amp.set_reference_source(int(v))),
            ("ref_trig",     lambda v: amp.set_reference_trigger(int(v))),
            ("sensitivity",  lambda v: amp.set_sensitivity(int(v))),
            ("reserve",      lambda v: amp.set_reserve_mode(int(v))),
            ("time_constant",lambda v: amp.set_time_constant(int(v))),
            ("filter_slope", lambda v: amp.set_low_pass_filter_slope(int(v))),
            ("sync_filter",  lambda v: amp.set_synchronous_filter(int(v))),
            ("input_cfg",    lambda v: amp.set_input_configuration(int(v))),
            ("input_gnd",    lambda v: amp.set_input_shield_grounding(int(v))),
            ("input_cpl",    lambda v: amp.set_input_coupling(int(v))),
            ("notch",        lambda v: amp.set_input_line_notch_filter(int(v))),
        ]
        for key, fn in _setters:
            if key in c and c[key] is not None:
                try: fn(c[key])
                except Exception as e: errs.append(f"{key}: {e}")
        logger.info(f"Config '{name}' applied to amplifier. Errors: {errs or 'none'}")
        if errs: return _err(f"✗ {len(errs)} error(s): {'; '.join(errs[:2])}")
        return _ok(f"✓ Config '{name}' applied. Click 'Read All Parameters' to refresh display.")

    # ── Configurations: populate editor from selection ────────────────────────
    @app.callback(
        Output("cfg-name",         "value"), Output("cfg-frequency",    "value"),
        Output("cfg-phase",        "value"), Output("cfg-sine-amp",     "value"),
        Output("cfg-harmonic",     "value"), Output("cfg-ref-src",      "value"),
        Output("cfg-ref-trig",     "value"), Output("cfg-sensitivity",  "value"),
        Output("cfg-reserve",      "value"), Output("cfg-time-constant","value"),
        Output("cfg-filter-slope", "value"), Output("cfg-sync-filter",  "value"),
        Output("cfg-input-cfg",    "value"), Output("cfg-input-gnd",    "value"),
        Output("cfg-input-cpl",    "value"), Output("cfg-notch",        "value"),
        Input("btn-edit-config", "n_clicks"),
        State("config-dropdown", "value"),
        State("config-store",    "data"),
        prevent_initial_call=True,
    )
    def cb_cfg_edit(_, name, cfgs):
        if not name or name not in (cfgs or {}):
            return [dash.no_update]*16
        c = cfgs[name]
        return (
            name, c.get("frequency"), c.get("phase"), c.get("sine_amp"),
            c.get("harmonic"), c.get("ref_src"), c.get("ref_trig"),
            c.get("sensitivity"), c.get("reserve"), c.get("time_constant"),
            c.get("filter_slope"), c.get("sync_filter"),
            c.get("input_cfg"), c.get("input_gnd"), c.get("input_cpl"), c.get("notch"),
        )

    # ── Configurations: clear editor ─────────────────────────────────────────
    @app.callback(
        Output("cfg-name",         "value", allow_duplicate=True),
        Output("cfg-frequency",    "value", allow_duplicate=True),
        Output("cfg-phase",        "value", allow_duplicate=True),
        Output("cfg-sine-amp",     "value", allow_duplicate=True),
        Output("cfg-harmonic",     "value", allow_duplicate=True),
        Output("cfg-ref-src",      "value", allow_duplicate=True),
        Output("cfg-ref-trig",     "value", allow_duplicate=True),
        Output("cfg-sensitivity",  "value", allow_duplicate=True),
        Output("cfg-reserve",      "value", allow_duplicate=True),
        Output("cfg-time-constant","value", allow_duplicate=True),
        Output("cfg-filter-slope", "value", allow_duplicate=True),
        Output("cfg-sync-filter",  "value", allow_duplicate=True),
        Output("cfg-input-cfg",    "value", allow_duplicate=True),
        Output("cfg-input-gnd",    "value", allow_duplicate=True),
        Output("cfg-input-cpl",    "value", allow_duplicate=True),
        Output("cfg-notch",        "value", allow_duplicate=True),
        Input("btn-clear-editor", "n_clicks"),
        prevent_initial_call=True,
    )
    def cb_cfg_clear(_):
        return [None]*16

    # ── Display channels: auto-refresh at 500ms ───────────────────────────────
    @app.callback(
        Output("display-ch1-val", "children"),
        Output("display-ch2-val", "children"),
        Input("display-interval", "n_intervals"),
        prevent_initial_call=False,
    )
    def cb_display_refresh(_):
        def safe_outr(ch):
            try: return f"{amp.display_value(ch):.6g}"
            except Exception as e: return f"✗ {e}"
        return safe_outr(1), safe_outr(2)

    # ── Display channels: Apply (sets DDEF + FPOP together) ──────────────────
    @app.callback(
        Output("status-ddef", "children"),
        Input("btn-set-ddef1", "n_clicks"),
        Input("btn-set-ddef2", "n_clicks"),
        State("ddef1-param", "value"),
        State("ddef1-ratio", "value"),
        State("fpop1-src",   "value"),
        State("ddef2-param", "value"),
        State("ddef2-ratio", "value"),
        State("fpop2-src",   "value"),
        prevent_initial_call=True,
    )
    def cb_set_display(n1, n2, p1, r1, f1, p2, r2, f2):
        ctx = dash.callback_context
        t = ctx.triggered[0]["prop_id"].split(".")[0]
        try:
            if t == "btn-set-ddef1":
                amp.set_display_config(1, int(p1 or 0), int(r1 or 0))
                if f1 is not None: amp.set_front_panel_output(1, int(f1))
                return _ok(f"✓ CH1 → {amp.DISPLAY_PARAM[int(p1 or 0)]}")
            if t == "btn-set-ddef2":
                amp.set_display_config(2, int(p2 or 0), int(r2 or 0))
                if f2 is not None: amp.set_front_panel_output(2, int(f2))
                return _ok(f"✓ CH2 → {amp.DISPLAY_PARAM[int(p2 or 0)]}")
        except Exception as e:
            return _err(f"✗ {e}")
        return ""

    # ── Periodic measurement: toggle ─────────────────────────────────────────
    @app.callback(
        Output("periodic-interval", "disabled"),
        Output("periodic-interval", "interval"),
        Output("btn-periodic-toggle", "children"),
        Output("btn-periodic-toggle", "style"),
        Input("btn-periodic-toggle", "n_clicks"),
        State("in-periodic-interval", "value"),
        State("periodic-interval", "disabled"),
        prevent_initial_call=True,
    )
    def cb_periodic_toggle(_, secs, is_disabled):
        new_disabled = not is_disabled
        interval_ms = max(1000, int((secs or 5) * 1000))
        if new_disabled:
            return True, interval_ms, "▶ Start", _SIDEBAR_BTN
        else:
            return False, interval_ms, "⏹ Stop", {
                **_SIDEBAR_BTN, "background": "#7b1e1e",
            }

    # ── Periodic measurement: snapshot on interval ────────────────────────────
    @app.callback(
        Output("recordings-store", "data", allow_duplicate=True),
        Output("status-periodic",  "children"),
        Input("periodic-interval", "n_intervals"),
        State("recordings-store",  "data"),
        prevent_initial_call=True,
    )
    def cb_periodic_snapshot(_, records):
        rec = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}
        try:
            params = amp.read_all_params()
            if "X"     in params: params["X"]     = round(params["X"],     8)
            if "Y"     in params: params["Y"]     = round(params["Y"],     8)
            if "R"     in params: params["R"]     = round(params["R"],     8)
            if "theta" in params: params["theta"] = round(params["theta"], 5)
            rec.update(params)
        except Exception as e:
            logger.warning(f"Periodic snapshot failed: {e}")
        records = list(records or [])
        records.append(rec)
        return records, _ok(f"✓ Auto #{len(records)}")

    # ── Quick-apply config: show confirm dialog ───────────────────────────────
    @app.callback(
        Output("confirm-quick-cfg", "displayed"),
        Output("confirm-quick-cfg", "message"),
        Output("pending-quick-cfg", "data"),
        Input("nav-quick-cfg", "value"),
        prevent_initial_call=True,
    )
    def cb_quick_cfg_confirm(name):
        if not name:
            return False, "", None
        return True, f"Apply configuration '{name}' to the amplifier?", name

    # ── Quick-apply config: apply on confirm, reset on cancel ─────────────────
    @app.callback(
        Output("nav-quick-cfg",        "value"),
        Output("pending-quick-cfg",    "data",     allow_duplicate=True),
        Output("cfg-action-status",    "children", allow_duplicate=True),
        Input("confirm-quick-cfg",     "submit_n_clicks"),
        Input("confirm-quick-cfg",     "cancel_n_clicks"),
        State("pending-quick-cfg",     "data"),
        State("config-store",          "data"),
        prevent_initial_call=True,
    )
    def cb_quick_cfg_apply(submit, cancel, name, cfgs):
        ctx = dash.callback_context
        prop_id = ctx.triggered[0]["prop_id"]
        if "submit_n_clicks" not in prop_id or not name or name not in (cfgs or {}):
            return None, None, ""
        c = cfgs[name]; errs = []
        _setters = [
            ("frequency",    lambda v: amp.set_frequency(float(v))),
            ("phase",        lambda v: amp.set_phase(float(v))),
            ("sine_amp",     lambda v: amp.set_sine_amplitude(float(v))),
            ("harmonic",     lambda v: amp.set_detection_harmonic(int(v))),
            ("ref_src",      lambda v: amp.set_reference_source(int(v))),
            ("ref_trig",     lambda v: amp.set_reference_trigger(int(v))),
            ("sensitivity",  lambda v: amp.set_sensitivity(int(v))),
            ("reserve",      lambda v: amp.set_reserve_mode(int(v))),
            ("time_constant",lambda v: amp.set_time_constant(int(v))),
            ("filter_slope", lambda v: amp.set_low_pass_filter_slope(int(v))),
            ("sync_filter",  lambda v: amp.set_synchronous_filter(int(v))),
            ("input_cfg",    lambda v: amp.set_input_configuration(int(v))),
            ("input_gnd",    lambda v: amp.set_input_shield_grounding(int(v))),
            ("input_cpl",    lambda v: amp.set_input_coupling(int(v))),
            ("notch",        lambda v: amp.set_input_line_notch_filter(int(v))),
        ]
        for key, fn in _setters:
            if key in c and c[key] is not None:
                try: fn(c[key])
                except Exception as e: errs.append(f"{key}: {e}")
        logger.info(f"Quick-apply config '{name}' applied. Errors: {errs or 'none'}")
        if errs:
            return None, None, _err(f"✗ {len(errs)} error(s): {'; '.join(errs[:2])}")
        return None, None, _ok(f"✓ Config '{name}' applied.")

    return app
