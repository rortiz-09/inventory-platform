"""
Server Governance Platform - Chart Components
Plotly visualizations with dark theme styling.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional, Dict, List


# Dark theme color palette
COLORS = {
    'primary': '#3b82f6',
    'secondary': '#8b5cf6',
    'success': '#22c55e',
    'warning': '#eab308',
    'danger': '#ef4444',
    'info': '#06b6d4',
    'muted': '#64748b',
    'background': '#0f172a',
    'surface': '#1e293b',
    'text': '#e2e8f0',
    'text_muted': '#94a3b8',
}

# Consistent color sequence for charts
COLOR_SEQUENCE = [
    '#3b82f6',  # Blue
    '#8b5cf6',  # Purple
    '#06b6d4',  # Cyan
    '#22c55e',  # Green
    '#eab308',  # Yellow
    '#f97316',  # Orange
    '#ef4444',  # Red
    '#ec4899',  # Pink
]

# Base layout for all charts
BASE_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color=COLORS['text'], family='Inter, sans-serif'),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(
        bgcolor='rgba(0,0,0,0)',
        borderwidth=0,
        font=dict(size=11),
    ),
)


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply consistent dark theme to a Plotly figure."""
    fig.update_layout(**BASE_LAYOUT)
    fig.update_xaxes(
        gridcolor='rgba(255,255,255,0.05)',
        tickfont=dict(color=COLORS['text_muted']),
    )
    fig.update_yaxes(
        gridcolor='rgba(255,255,255,0.05)',
        tickfont=dict(color=COLORS['text_muted']),
    )
    return fig


def environment_distribution_chart(data: pd.DataFrame) -> go.Figure:
    """
    Create a donut chart showing server distribution by environment.
    
    Args:
        data: DataFrame with 'environment' column
    """
    if data.empty or 'environment' not in data.columns:
        return empty_chart("Sin datos de ambiente")
    
    counts = data['environment'].value_counts().reset_index()
    counts.columns = ['environment', 'count']
    
    fig = go.Figure(data=[go.Pie(
        labels=counts['environment'],
        values=counts['count'],
        hole=0.6,
        marker=dict(colors=COLOR_SEQUENCE),
        textinfo='label+percent',
        textposition='outside',
        textfont=dict(size=12),
    )])
    
    fig.update_layout(
        title=dict(text='Distribución por Ambiente', x=0.5, font=dict(size=16)),
        showlegend=True,
        legend=dict(orientation='h', y=-0.1),
        annotations=[dict(
            text=f'{len(data)}<br><span style="font-size:10px">Total</span>',
            x=0.5, y=0.5,
            font=dict(size=24, color=COLORS['text']),
            showarrow=False,
        )]
    )
    
    return apply_dark_theme(fig)


def server_type_chart(data: pd.DataFrame) -> go.Figure:
    """
    Create a donut chart for Physical vs Virtual distribution.
    
    Args:
        data: DataFrame with 'server_type' column
    """
    if data.empty or 'server_type' not in data.columns:
        return empty_chart("Sin datos de tipo de servidor")
    
    counts = data['server_type'].value_counts().reset_index()
    counts.columns = ['type', 'count']
    
    colors_map = {
        'FISICO': COLORS['primary'],
        'VIRTUAL': COLORS['secondary'],
        'DESCONOCIDO': COLORS['muted'],
    }
    
    colors = [colors_map.get(t, COLORS['muted']) for t in counts['type']]
    
    fig = go.Figure(data=[go.Pie(
        labels=counts['type'],
        values=counts['count'],
        hole=0.65,
        marker=dict(colors=colors),
        textinfo='label+value',
        textposition='outside',
    )])
    
    fig.update_layout(
        title=dict(text='Físico vs Virtual', x=0.5, font=dict(size=16)),
        showlegend=False,
    )
    
    return apply_dark_theme(fig)


def top_os_chart(data: pd.DataFrame, top_n: int = 8) -> go.Figure:
    """
    Create a horizontal bar chart for top operating systems.
    
    Args:
        data: DataFrame with 'os_product_key' column
        top_n: Number of top OS to show
    """
    if data.empty or 'os_product_key' not in data.columns:
        return empty_chart("Sin datos de sistema operativo")
    
    counts = data['os_product_key'].value_counts().head(top_n).reset_index()
    counts.columns = ['os', 'count']
    counts = counts.sort_values('count', ascending=True)
    
    fig = go.Figure(data=[go.Bar(
        x=counts['count'],
        y=counts['os'],
        orientation='h',
        marker=dict(
            color=COLORS['primary'],
            line=dict(width=0),
        ),
        text=counts['count'],
        textposition='outside',
        textfont=dict(color=COLORS['text']),
    )])
    
    fig.update_layout(
        title=dict(text=f'Top {top_n} Sistemas Operativos', x=0.5, font=dict(size=16)),
        xaxis_title='',
        yaxis_title='',
        showlegend=False,
        height=300,
    )
    
    return apply_dark_theme(fig)


def health_score_distribution(data: pd.DataFrame) -> go.Figure:
    """
    Create a histogram of health scores.
    
    Args:
        data: DataFrame with 'health_score' column
    """
    if data.empty or 'health_score' not in data.columns:
        return empty_chart("Sin datos de health score")
    
    # Create bins for risk levels
    bins = [0, 40, 60, 80, 100]
    labels = ['Crítico', 'Alto', 'Medio', 'Bajo']
    colors = [COLORS['danger'], COLORS['warning'], '#f97316', COLORS['success']]
    
    data['risk_category'] = pd.cut(data['health_score'], bins=bins, labels=labels, include_lowest=True)
    counts = data['risk_category'].value_counts().reindex(labels).fillna(0)
    
    fig = go.Figure(data=[go.Bar(
        x=labels,
        y=counts.values,
        marker=dict(color=colors),
        text=counts.values.astype(int),
        textposition='outside',
        textfont=dict(color=COLORS['text']),
    )])
    
    fig.update_layout(
        title=dict(text='Distribución de Riesgo', x=0.5, font=dict(size=16)),
        xaxis_title='',
        yaxis_title='Cantidad de Servidores',
        showlegend=False,
        height=300,
    )
    
    return apply_dark_theme(fig)


def eol_timeline_chart(data: pd.DataFrame) -> go.Figure:
    """
    Create a timeline showing upcoming EOL dates.
    
    Args:
        data: DataFrame with 'eol_date' column
    """
    if data.empty or 'eol_date' not in data.columns:
        return empty_chart("Sin datos de EOL")
    
    # Filter to only servers with EOL dates
    eol_data = data[data['eol_date'].notna()].copy()
    
    if eol_data.empty:
        return empty_chart("Sin fechas EOL registradas")
    
    # Group by month
    eol_data['eol_month'] = pd.to_datetime(eol_data['eol_date']).dt.to_period('M')
    monthly = eol_data.groupby('eol_month').size().reset_index(name='count')
    monthly['eol_month'] = monthly['eol_month'].astype(str)
    
    fig = go.Figure(data=[go.Scatter(
        x=monthly['eol_month'],
        y=monthly['count'],
        mode='lines+markers',
        line=dict(color=COLORS['danger'], width=2),
        marker=dict(size=8, color=COLORS['danger']),
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.1)',
    )])
    
    fig.update_layout(
        title=dict(text='Timeline de EOL', x=0.5, font=dict(size=16)),
        xaxis_title='Mes',
        yaxis_title='Servidores',
        height=300,
    )
    
    return apply_dark_theme(fig)


def city_distribution_chart(data: pd.DataFrame) -> go.Figure:
    """
    Create a sunburst chart for environment/city distribution.
    
    Args:
        data: DataFrame with 'environment' and 'city' columns
    """
    if data.empty:
        return empty_chart("Sin datos de ubicación")
    
    # Prepare hierarchical data
    grouped = data.groupby(['environment', 'city']).size().reset_index(name='count')
    
    fig = go.Figure(go.Sunburst(
        labels=list(grouped['environment']) + list(grouped['city'].unique()),
        parents=[''] * len(grouped) + list(grouped['environment']),
        values=list(grouped['count']) + [0] * len(grouped['city'].unique()),
        branchvalues='total',
        marker=dict(colors=COLOR_SEQUENCE),
    ))
    
    # Simpler approach with treemap
    fig = px.sunburst(
        grouped,
        path=['environment', 'city'],
        values='count',
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    
    fig.update_layout(
        title=dict(text='Servidores por Ambiente y Ciudad', x=0.5, font=dict(size=16)),
        height=350,
    )
    
    return apply_dark_theme(fig)


def health_gauge(score: int) -> go.Figure:
    """
    Create a gauge chart for average health score.
    
    Args:
        score: Average health score (0-100)
    """
    # Determine color based on score
    if score >= 80:
        color = COLORS['success']
    elif score >= 60:
        color = COLORS['warning']
    else:
        color = COLORS['danger']
    
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=score,
        domain=dict(x=[0, 1], y=[0, 1]),
        title=dict(text='Health Score Promedio', font=dict(size=14, color=COLORS['text'])),
        number=dict(font=dict(size=40, color=color)),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=COLORS['text_muted']),
            bar=dict(color=color),
            bgcolor=COLORS['surface'],
            borderwidth=0,
            steps=[
                dict(range=[0, 40], color='rgba(239, 68, 68, 0.2)'),
                dict(range=[40, 60], color='rgba(234, 179, 8, 0.2)'),
                dict(range=[60, 80], color='rgba(249, 115, 22, 0.2)'),
                dict(range=[80, 100], color='rgba(34, 197, 94, 0.2)'),
            ],
            threshold=dict(
                line=dict(color=COLORS['text'], width=2),
                thickness=0.75,
                value=score,
            ),
        ),
    ))
    
    fig.update_layout(height=250)
    
    return apply_dark_theme(fig)


def empty_chart(message: str = "Sin datos disponibles") -> go.Figure:
    """Create an empty state chart with message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref='paper', yref='paper',
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color=COLORS['muted']),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=200,
    )
    return apply_dark_theme(fig)


def backup_coverage_chart(data: pd.DataFrame) -> go.Figure:
    """
    Create a pie chart showing backup coverage.
    
    Args:
        data: DataFrame with 'backup_enabled' column
    """
    if data.empty or 'backup_enabled' not in data.columns:
        return empty_chart("Sin datos de backup")
    
    counts = data['backup_enabled'].value_counts()
    labels = ['Con Backup' if k else 'Sin Backup' for k in counts.index]
    colors = [COLORS['success'] if k else COLORS['danger'] for k in counts.index]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=counts.values,
        hole=0.6,
        marker=dict(colors=colors),
        textinfo='percent',
        textposition='inside',
    )])
    
    fig.update_layout(
        title=dict(text='Cobertura de Backup', x=0.5, font=dict(size=16)),
        showlegend=True,
        legend=dict(orientation='h', y=-0.1),
    )
    
    return apply_dark_theme(fig)
