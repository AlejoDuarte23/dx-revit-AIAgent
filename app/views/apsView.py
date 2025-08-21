import plotly.graph_objects as go
import viktor as vkt

from pathlib import Path

class APSView(vkt.WebView):
    pass

class APSresult(vkt.WebResult):
    """Wrap ApsViewer.html and inject token + URN."""

    def __init__(self, urn_b64: str, token: str):
        html = (Path(__file__).parent / "ApsViewer_Filter.html").read_text()
        html = html.replace("APS_TOKEN_PLACEHOLDER", token)
        html = html.replace("URN_PLACEHOLDER", urn_b64)
        super().__init__(html=html)



def default_blank_scene()->go.Figure:
    """Fallback scene when there is no Plotly objects to plot!"""
    fig = go.Figure()
    fig.update_layout(
        template=None,
        xaxis=dict(visible=False, showgrid=False, zeroline=False, showline=False),
        yaxis=dict(visible=False, showgrid=False, zeroline=False, showline=False),
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=0, b=0),
        autosize=True,
    )
    return fig
