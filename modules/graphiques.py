import plotly.graph_objects as go
import plotly.express as px

def graphique_totaux(totaux):
    """Crée un graphique bar des totaux par magasin."""
    fig = go.Figure(data=[
        go.Bar(
            x=list(totaux.keys()),
            y=list(totaux.values()),
            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        )
    ])
    fig.update_layout(
        title="Total du panier par magasin",
        xaxis_title="Magasin",
        yaxis_title="Prix total (€)",
        showlegend=False
    )
    return fig

def graphique_ecarts(ecarts):
    """Crée un graphique des écarts de prix."""
    fig = go.Figure()
    
    if not ecarts:
        fig.update_layout(
            title="Aucun écart de prix à afficher",
            xaxis_title="Article",
            yaxis_title="Écart (€)",
            showlegend=False
        )
        return fig
    
    articles = list(ecarts.keys())
    ecarts_vals = [ecarts[a]['ecart'] for a in articles]
    
    fig = go.Figure(data=[
        go.Bar(
            x=articles,
            y=ecarts_vals,
            marker_color='#FF6B6B'
        )
    ])
    fig.update_layout(
        title="Écarts de prix par article (max - min)",
        xaxis_title="Article",
        yaxis_title="Écart (€)",
        showlegend=False
    )
    return fig
