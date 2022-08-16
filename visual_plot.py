import pandas as pd 
import plotly.express as px
import plotly.graph_objs as go
import joblib
from PIL import Image
from dash.dependencies import Input, Output
from dash import dcc
from dash import html
import dash


img = Image.open('./map.png')

def visual_plot(ch):
    pos_data = ch
    
    print('pos_data', pos_data)
    print('len pos_data', len(pos_data))

    return pos_data

app = dash.Dash(__name__)
fig = go.Figure()
app.layout = html.Div(
children = [
    dcc.Graph(id = 'live-graph', figure = fig),
    dcc.Interval(
        id = 'graph-update',
        interval = 1020,
        n_intervals = 0
    ),

])

@app.callback(
    Output('live-graph', 'figure'),
    [ Input('graph-update', 'n_intervals') ]
)
def visual_plot_fig(n_intervals):
    while True:
        try:
            working_dir1 = "./initial_predicted.csv"
            print('updated')
            break
        except FileNotFoundError as e:
            continue
    while True:
        try:
            ch = pd.read_csv(working_dir1)
            break
        except pd.errors.EmptyDataError:
            break
        except FileNotFoundError:
            ch = pd.DataFrame(columns=['X','Y','Z','W','MAC_Seq','Time'])
            break
    pos_data = visual_plot(ch)


    fig = go.Figure()
    site_info = joblib.load('./map_info.pkl')
    if site_info and 'loaded_map' in site_info:                
        loaded_map = site_info['loaded_map']
        x_off, y_off = loaded_map['offsets']
        x_span, y_span = loaded_map['spans']
        fig.add_layout_image(
            dict(
                source=loaded_map['pil_img'],
                xref='x',
                yref='y',
                x=x_off,
                y=y_off + y_span,
                sizex=x_span,
                sizey=y_span,
                sizing="stretch",
                layer="below")
        )
        fig.update_xaxes(range=[-28.85, 38.3], autorange=False)
        fig.update_yaxes(range=[-12, 23.35], autorange=False)    

    px_fig = px.scatter(
        pos_data, 
        x='X', 
        y='Y', 
        color='MAC_Seq',
        symbol = 'MAC_Seq',
        labels={
                "MAC_Seq": "MAC Address",
                 },
    )

    fig.add_traces(px_fig['data'])
    fig.update_traces(marker_size=15)

    fig.update_layout(
    title="Passive Wi-Fi IPS",
    title_x=0.5,
    legend=dict(
    title="Wi-Fi Clients",
    font=dict(size=16)
),
    height=600,
    width=1200,
    margin=dict(l=10, r=10, t=50, b=10),
)
    return fig


if __name__ == '__main__':
        visual_plot_fig(None)
        app.run_server(debug=True, port=8500, host='0.0.0.0')





