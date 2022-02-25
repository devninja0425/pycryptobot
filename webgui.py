import json
import os
import dash
# import datetime
from datetime import datetime, timedelta
from dash import html, dcc, State
import dash_table
import dash_daq as daq
# from dash.dash_table.Format import Format, Scheme
from dash.dash_table import FormatTemplate
import pandas as pd
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

# from models.telegram import Wrapper
from pages import controls, config

external_stylesheets = [dbc.themes.DARKLY]
#To change the theme just insert the name in the line above.
#The full list of available themes is CERULEAN, COSMO, CYBORG, DARKLY, FLATLY, JOURNAL, LITERA, LUMEN, 
#LUX, MATERIA, MINTY, MORPH, PULSE, QUARTZ, SANDSTONE, SIMPLEX, SKETCHY, SLATE, SOLAR, SPACELAB, SUPERHERO, UNITED, VAPOR, YETI, ZEPHYR

tg_wrapper = controls.tg_wrapper # Wrapper('config.json')
json_dir = tg_wrapper.helper.datafolder

df=[]
dff=[]
df_margin=0
app = dash.Dash(__name__, title = 'Pycryptobot Dashboard', external_stylesheets=external_stylesheets, update_title=None, meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ])

percentage = FormatTemplate.percentage(2)

CONTENT_STYLE = {
    "margin-left": "1rem",
    "margin-right": "1rem",
    "padding": "0rem 1rem",
}

app.layout = html.Div(children=[
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Dashboard", href="/")),
        dbc.NavItem(dbc.NavLink("Controls", href="/controls")),
        dbc.NavItem(dbc.NavLink("Edit Config", href="/config")),
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Bot Options", header=True),
                dbc.DropdownMenuItem("Controls", href="/controls"),
                dbc.DropdownMenuItem("Config Editor", href="/config"),
            ],
            nav=True,
            in_navbar=True,
            label="More",
        ),
    ],
    brand="Pycryptobot",
    brand_style={'textAlign':'left'},
    brand_href="/",
    color="primary", #primary
    dark=True,
    fluid=True,
    fixed=True
    ),
    html.Div(id='page-content', style=CONTENT_STYLE)])

dashboard_layout = html.Div(children=[
    dbc.Row(
        dbc.Col([html.H4('Dashboard', style={'textAlign':'left'}),], width={'size':1}),
        ),

    html.Br(),
    dbc.Row([
        dbc.Col([
            dash_table.DataTable(
                id='table-paging-and-sorting',
                page_action="native",
                page_current= 0,
                page_size= 15,
                sort_action="native",
                style_cell={'textAlign': 'center'},
                style_as_list_view=True,
                editable=True,
                columns=[
                        {'name': 'Uptime', 'id': 'Uptime', 'type': 'text'},
                        {'name': 'Trading Pair', 'id': 'Trading Pair', 'type': 'text'},
                        {'name': 'Exchange', 'id': 'Exchange', 'type': 'text'},
                        {'name': 'Last Action', 'id': 'Last Action', 'type': 'numeric'},
                        {'name': 'Current Price', 'id': 'Current Price', 'type': 'numeric'},
                        dict(id='Margin', name='Margin', type='numeric', format=percentage),
                        #{'name': 'Margin', 'id': 'Margin', 'type': 'numeric', 'format': 'percentage'},
                        {'name': 'TSLT', 'id': 'TSLT', 'type': 'text'},
                        {'name': 'PVLT', 'id': 'PVLT', 'type': 'text'},
                        dict(id='From DF High', name='From DF High', type='numeric', format=percentage),                
                        #{'name': 'From DF High', 'id': 'From DF High', 'type': 'numeric'},
                        {'name': 'DF High', 'id': 'DF High', 'type': 'numeric'},
                        {'name': 'Delta', 'id': 'Delta', 'type': 'numeric'},
                        {'name': 'BULL', 'id': 'BULL', 'type': 'text'},
                        {'name': 'ERI', 'id': 'ERI', 'type': 'text'},
                        {'name': 'EMA', 'id': 'EMA', 'type': 'text'},
                        {'name': 'MACD', 'id': 'MACD', 'type': 'text'},
                        {'name': 'OBV', 'id': 'OBV', 'type': 'text'},  
                    ],
                style_header={
                        'backgroundColor': 'rgb(30, 30, 30)',
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                style_data={
                        'backgroundColor': 'rgb(50, 50, 50)',
                        'color': 'white'
                    }, 

                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(70, 70, 70)',
                        },
                    #set column widths    
                    {'if': {'column_id': 'Trading Pair'},'width': '180px'},
                    {'if': {'column_id': 'Last Action'},'width': '130px'},
                    {'if': {'column_id': 'Current Price'},'width': '160px'},
                    {'if': {'column_id': 'Margin'},'width': '160px'},
                    {'if': {'column_id': 'TSLT'},'width': '80px'},
                    {'if': {'column_id': 'PVLT'},'width': '80px'},
                    {'if': {'column_id': 'From DF High'},'width': '130px'},
                    {'if': {'column_id': 'DF High'},'width': '130px'},
                    {'if': {'column_id': 'BULL'},'width': '80px'},
                    {'if': {'column_id': 'ERI'},'width': '80px'},
                    {'if': {'column_id': 'EMA'},'width': '80px'},
                    {'if': {'column_id': 'MACD'},'width': '80px'},
                    {'if': {'column_id': 'OBV'},'width': '80px'},

        ###indicator states
        ###add gradients for from_df_hi and margins to represent position, when from df high is > 0 make df hi green

                    {'if': 
                        {'filter_query': '{Margin} > 0', 'column_id': 'Margin'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{Margin} < 0', 'column_id': 'Margin'},
                        'backgroundColor': '#99413d',
                        'color': 'white'
                    },            
                    {'if': {'filter_query': '{From DF High} > 0', 'column_id': 'From DF High'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{From DF High} < 0', 'column_id': 'From DF High'},
                        'backgroundColor': '#99413d',
                        'color': 'white'
                    },      
                    {'if': {'filter_query': '{TSLT} = "True"', 'column_id': 'TSLT'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{PVLT} = "True"', 'column_id': 'PVLT'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{BULL} = "True"', 'column_id': 'BULL'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{BULL} = "False"', 'column_id': 'BULL'},
                        'backgroundColor': '#99413d',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{ERI} = "True"', 'column_id': 'ERI'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{ERI} = "False"', 'column_id': 'ERI'},
                        'backgroundColor': '#99413d',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{EMA} = "True"', 'column_id': 'EMA'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{EMA} = "False"', 'column_id': 'EMA'},
                        'backgroundColor': '#99413d',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{MACD} = "True"','column_id': 'MACD'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{MACD} = "False"','column_id': 'MACD'},
                        'backgroundColor': '#99413d',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{OBV} = "True"','column_id': 'OBV'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{OBV} = "False"', 'column_id': 'OBV'},
                        'backgroundColor': '#99413d',
                        'color': 'white'
                    },
                    {'if': {'filter_query': '{Last Action} != SELL', 'column_id': 'Last Action'},
                        'backgroundColor': '#3D9970',
                        'color': 'white'
                    },
            ],
        ),
    ], xs=10, sm=10, md=10, lg=12, xl=12),
    ]),

### update interval
    dcc.Interval(id='interval-container', interval = 10000, n_intervals = 0),

### graphs
    dbc.Row([
###margin graph
        dbc.Col([
                html.H5("Margin", style={'textAlign':'center'}),
                html.Div(id='margin-graph'),
            ], xs=12, sm=12, md=12, lg=6, xl=5),
###df high graph
        dbc.Col([
                html.H5("From DF High", style={'textAlign':'center'}),
                html.Div(id='from-df-high'),
            ], xs=12, sm=12, md=12, lg=6, xl=5),
        dbc.Col([
            html.Div(id='margin-current'),
            html.Div(id='margin-7Dtotal'),
            ],xs=10, sm=10, md=2, lg=1, xl=1,)
        ],justify="evenly",),

])

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')])
def display_page(pathname):
    """page navigation"""
    if pathname == '/controls':
        return controls.layout
    if pathname == "/config":
        return config.layout
    else:
        return dashboard_layout

### Bot instance uptime tracking
def getDateFromISO8601Str(date: str): #pylint: disable=invalid-name
    """Bot instance uptime tracking"""
    now = str(datetime.now())
    # If date passed from datetime.now() remove milliseconds
    if date.find(".") != -1:
        dt = date.split(".")[0]
        date = dt
    if now.find(".") != -1:
        dt = now.split(".")[0]
        now = dt
    
    now = now.replace("T", " ")
    now = f"{now}"
    # Add time in case only a date is passed in
    date = date.replace("T", " ") if date.find("T") != -1 else date
    # Add time in case only a date is passed in
    new_date_str = f"{date} 00:00:00" if len(date) == 10 else date

    started = datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")
    now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
    duration = now - started
    duration_in_s = duration.total_seconds()
    hours = divmod(duration_in_s, 3600)[0]
    duration_in_s -= 3600*hours
    minutes = divmod(duration_in_s, 60)[0]
    return f"{round(hours)}h {round(minutes)}m"

@app.callback(
        Output('table-paging-and-sorting','data'),
        Input('interval-container', 'n_intervals'),
        )
def update_table(n):
    """Update all data"""
    pairs_list = tg_wrapper.helper.get_active_bot_list() #glob.glob(json_pattern)
    df = pd.DataFrame(
    columns=['Uptime', 'Trading Pair', 'Exchange', 'Last Action', 'Current Price', 'From DF High', 'DF High', 
        'Margin', 'Delta', 'TSLT', 'PVLT', 'ERI', 'BULL', 'EMA', 'MACD', 'OBV'],

    )
    for pair in pairs_list:
        if not "data.json" in pair and not pair.__contains__("output.json") and not "settings.json" in pair:
            try:
                with open(os.path.join(tg_wrapper.helper.datafolder, 'telegram_data', f"{pair}.json"), encoding="utf8") as f:
                    json_data =pd.json_normalize(json.loads(f.read()))
                    json_data['pair'] = pair
                    uptime = getDateFromISO8601Str(json_data['botcontrol.started'][0])
                    if isinstance(json_data["margin"][0], str) and '%' in json_data["margin"][0] and '-' in json_data["margin"][0]:
                        margincolor = '#99413d'
                    elif isinstance(json_data["margin"][0], str) and '%' in json_data["margin"][0] and '-' not in json_data["margin"][0]:
                        margincolor = '#3D9970'
                    elif isinstance(json_data['from_df_high'][0], str) and '%' in json_data['from_df_high'][0] and '-' in json_data['from_df_high'][0]:
                        margincolor = '#99413d'
                    elif isinstance(json_data['from_df_high'][0], str) and '%' in json_data['from_df_high'][0] and '-' not in json_data['from_df_high'][0]:
                        margincolor = '#3D9970'
                    data = pd.DataFrame(
                            {
                                "Uptime": uptime,
                                "Trading Pair": json_data['pair'],
                                "Exchange": json_data["exchange"],
                                "Last Action": "SELL" if "margin" in json_data and json_data["margin"][0] == " " else "BUY",
                                "Current Price": json_data["price"],
                                "Margin": json_data["margin"] if "margin" in json_data and json_data["margin"][0] != " " else "NaN",
                                "TSLT": json_data["trailingstoplosstriggered"] if "trailingstoplosstriggered" in json_data else "",
                                "PVLT": json_data["preventlosstriggered"] if "preventlosstriggered" in json_data else "",
                                "From DF High": json_data['from_df_high'] if "from_df_high" in json_data and json_data['from_df_high'][0] != " " else "NaN",
                                "DF High": json_data['df_high'] if "df_high" in json_data else "",
                                "BULL": json_data["indicators.BULL"] if "indicators.BULL" in json_data else "",
                                "ERI" : json_data["indicators.ERI"] if "indicators.ERI" in json_data else "",
                                "EMA" : json_data["indicators.EMA"] if "indicators.EMA" in json_data else "",
                                "MACD": json_data["indicators.MACD"] if "indicators.MACD" in json_data else "",
                                "OBV": json_data["indicators.OBV"] if "indicators.OBV" in json_data else "",
                                "Margincolor": margincolor,
                            })
                df = df.append(data, ignore_index=True)
            except KeyError:
                print('oops')
            except Exception as err:
                print(err)

###change data types of dataframe for conditional statements
    df['Margin'] = df['Margin'].map(lambda x: x.rstrip('%'))
    df['Margin'] = df['Margin'].fillna(0)
    df['Margin'] = df['Margin'].astype(float, errors='ignore')
    df['Margin'] = df['Margin']*.01
    df_margin = (df['Margin'].mean())*100
    df['From DF High'] = df['From DF High'].map(lambda x: x.rstrip('%'))
    df['From DF High'] = df['From DF High'].fillna(0)
    df['From DF High'] = df['From DF High'].astype(float, errors='ignore')
    df['From DF High'] = df['From DF High']*.01
    df['TSLT'] = df['TSLT'].astype(str)
    df['PVLT'] = df['PVLT'].astype(str)
    df['BULL'] = df['BULL'].astype(str)
    df['ERI'] = df['ERI'].astype(str)
    df['EMA'] = df['EMA'].astype(str)
    df['MACD'] = df['MACD'].astype(str)
    df['OBV'] = df['OBV'].astype(str)
    df = df.sort_values(by="Last Action", ascending=[True], inplace=False)

    return df.to_dict(orient='records')

### create graphs
@app.callback(
    Output('margin-graph', "children"),
    Input('table-paging-and-sorting', "derived_virtual_data"),
    Input('table-paging-and-sorting', "derived_virtual_selected_rows"))
def update_graphs(rows, derived_virtual_selected_rows):
    """Update graphs"""
    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []

    dff = df if rows is None else pd.DataFrame(rows)
    dff['Margin'] = dff['Margin']*100
    dff['From DF High'] = dff['From DF High']*100
    colors = ['white' if i in derived_virtual_selected_rows else dff["Margincolor"]
            for i in range(len(dff))]
    
    return [
                dcc.Graph(
                    id="Margin",
                    figure={
                        "data": [
                            {
                                "x": dff['Trading Pair'],
                                "y": dff["Margin"],
                                "type": "bar",
                                "marker": {"color": colors[0],}, #[(-25,'#99413d'), (25,'#3D9970')]     
                            }
                        ],
                        "layout": {
                            "plot_bgcolor": "rgba(0,0,0,0)",
                            "paper_bgcolor": "rgba(0,0,0,0)",
                            "font": {"color": 'white'},
                            "xaxis": {"automargin": True},
                            "yaxis": {"automargin": True},
                            "orientation": 'h',
                            "height": 400,
                            "margin": {"t": 10, "l": 10, "r": 10},
                            },
                    },
                )
                for column in ["Margin"] if column in dff
]

@app.callback(
    Output('from-df-high', "children"),
    Input('table-paging-and-sorting', "derived_virtual_data"),
    Input('table-paging-and-sorting', "derived_virtual_selected_rows"))
def update_graphs1(rows, derived_virtual_selected_rows):
    """ Update Graphs """
    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []

    dff = df if rows is None else pd.DataFrame(rows)
    dff['From DF High'] = dff['From DF High']*100
    colors = ['white' if i in derived_virtual_selected_rows else dff["Margincolor"]
            for i in range(len(dff))]
    
    return [
                dcc.Graph(
                    id="From DF High",
                    figure={
                        "data": [
                            {
                                "x": dff['Trading Pair'],
                                "y": dff["From DF High"],
                                "type": "bar",
                                "marker": {"color": colors[0],},
                            }
                        ],
                        "layout": {
                            "plot_bgcolor": "rgba(0,0,0,0)",
                            "paper_bgcolor": "rgba(0,0,0,0)",
                            "font": {"color": 'white'},
                            "xaxis": {"automargin": True},
                            "yaxis": {"automargin": True},
                            "orientation": 'h',
                            "height": 400,
                            #"width": 750, ### this is roughly half screen width
                            "margin": {"t": 10, "l": 10, "r": 10},
                            },
                    },
                )
                for column in ["From DF High"] if column in dff
]

### Active Margins Gauge
@app.callback(
    Output('margin-current','children'),
    Input('table-paging-and-sorting', "derived_virtual_data"),
    Input('table-paging-and-sorting', "derived_virtual_selected_rows"))
def gauge1(rows, derived_virtual_selected_rows):
    """ Active Margins Gauge """
    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []

    dff = df if rows is None else pd.DataFrame(rows)
    df_margin=(dff['Margin'].mean())*100

    return [
                daq.Gauge(
                label='Current Margins',
                id='margin-current',
                color={"gradient":True,"ranges":{'#99413d':[-35,-20],'#F1C232':[-20,20],'#3D9970':[20,35]}},
                value=df_margin,
                max=35,
                min=-35,
                size=160,
                ),
]

### 7 Day Total Margins Gauge
@app.callback(
        Output('margin-7Dtotal','children'), # ### gauge CALL BACK NOT WORKING 
        Input('table-paging-and-sorting', "derived_virtual_data"),
        Input('table-paging-and-sorting', "derived_virtual_selected_rows"))

def gauge2(rows, derived_virtual_selected_rows): 
    days = -7
    trade_counter = 0
    margin_calculation = 0
    trades_dir = 'telegram_data'
    json_pattern = os.path.join(trades_dir, 'data.json')
    today = datetime.now()
    week = today + \
                    timedelta(days)
 
    with open(json_pattern) as f:
        json_data =json.loads(f.read())

    for trade_datetime in json_data['trades']:       
        if datetime.strptime(trade_datetime, '%Y-%m-%d %H:%M:%S').isoformat() > week.isoformat():

            trade_counter += 1
            margin = float(json_data['trades'][trade_datetime]['margin'][: json_data['trades'][trade_datetime]['margin'].find("%")])
            margin_calculation += margin

    avg_margin = margin_calculation/trade_counter

    return [
                daq.Gauge(
                label='7 Day Margins',
                id='margin-7Dtotal',
                color={"gradient":True,"ranges":{'#99413d':[-100,-20],'#F1C232':[-20,20],'#3D9970':[20,100]}},
                value=margin_calculation,
                max=100,
                min=-100,
                size=160,
                ),
]

if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port="8051") # comment this line out if you want to run on just local machine @ 127.0.0.1:8050
    app.run_server(debug=True)

