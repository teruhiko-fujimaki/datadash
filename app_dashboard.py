import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px

# --- 1. データの準備とクレンジング ---
DATA_FILE = 'data.csv'

try:
    # データファイルの読み込み
    df = pd.read_csv(DATA_FILE)
    print(f"'{DATA_FILE}' を正常に読み込みました。")
    
except FileNotFoundError:
    print(f"エラー: '{DATA_FILE}' が見つかりません。ファイルを確認してください。")
    df = pd.DataFrame()
    
if not df.empty:
    # 列名の整理と型変換
    # 日本語の列名を内部的に使いやすい英語名にマッピング
    df.rename(columns={
        '契約日時': 'ContractDate',
        'キャンセル日時': 'CancellationDate',
        '価格': 'Price',
        '商品名': 'ProductName',
        '性別': 'Gender',
        '年齢': 'Age'
    }, inplace=True)

    # 日付列の処理
    df['ContractDate'] = pd.to_datetime(df['ContractDate'], errors='coerce')
    df['CancellationDate'] = pd.to_datetime(df['CancellationDate'], errors='coerce')
    
    # 重要な列の欠損値の除去
    df.dropna(subset=['ContractDate', 'Price', 'Gender', 'ProductName'], inplace=True)
    df.sort_values('ContractDate', inplace=True)

    # **【NEW: キャンセルフラグの作成】**
    # CancellationDateがNaNでない場合にキャンセル済みとする
    df['IsCancelled'] = df['CancellationDate'].notna()
    
    # 年齢グループの作成 (分析の粒度を下げる)
    bins = [0, 20, 30, 40, 50, 60, 70, 100]
    labels = ['~19', '20s', '30s', '40s', '50s', '60s', '70+']
    df['AgeGroup'] = pd.cut(df['Age'], bins=bins, labels=labels, right=False, ordered=True)

    # フィルター用のオプションを設定
    gender_options = [{'label': i, 'value': i} for i in df['Gender'].unique()]
    gender_options.insert(0, {'label': '全て', 'value': 'All'})

    product_options = [{'label': i, 'value': i} for i in df['ProductName'].unique()]
    product_options.insert(0, {'label': '全て', 'value': 'All'})

else:
    # データが空の場合のダミーオプション
    gender_options = [{'label': '全て', 'value': 'All'}]
    product_options = [{'label': '全て', 'value': 'All'}]


# --- 2. Dash アプリの初期化 ---
app = dash.Dash(__name__, title="顧客分析ダッシュボード")


# --- 3. レイアウトの定義 ---
app.layout = html.Div(style={'backgroundColor': '#f3f4f6', 'padding': '20px', 'minHeight': '100vh'}, children=[
    
    # タイトル
    html.H1("顧客データ分析ダッシュボード", style={
        'textAlign': 'center', 
        'color': '#1f2937', 
        'marginBottom': '30px', 
        'fontFamily': 'sans-serif',
        'fontWeight': '700'
    }),
    
    # フィルターコントロールパネル
    html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px', 'maxWidth': '1200px', 'margin': '0 auto 30px'}, children=[
        
        # 性別フィルター
        html.Div(style={'width': '50%', 'padding': '15px', 'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.08)'}, children=[
            html.Label("性別フィルター", style={'color': '#4b5563', 'fontWeight': 'bold', 'fontSize': '1.1em', 'marginBottom': '5px'}),
            dcc.Dropdown(
                id='gender-filter',
                options=gender_options,
                value='All',
                clearable=False,
            ),
        ]),
        
        # 商品名フィルター
        html.Div(style={'width': '50%', 'padding': '15px', 'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.08)'}, children=[
            html.Label("商品名フィルター", style={'color': '#4b5563', 'fontWeight': 'bold', 'fontSize': '1.1em', 'marginBottom': '5px'}),
            dcc.Dropdown(
                id='product-filter',
                options=product_options,
                value='All',
                clearable=False,
            ),
        ]),
    ]),
    
    # グラフエリア
    html.Div(style={'maxWidth': '1200px', 'margin': '0 auto', 'display': 'flex', 'flexDirection': 'column', 'gap': '30px'}, children=[
        
        # 1. 時系列売上トレンドグラフ
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.08)'}, children=[
            html.H3("月別総売上推移 (価格の合計)", style={'color': '#1f2937', 'borderBottom': '2px solid #3b82f6', 'paddingBottom': '10px'}),
            dcc.Graph(id='sales-time-series')
        ]),
        
        # 2. 年齢グループと性別による契約数分布
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.08)'}, children=[
            html.H3("年齢グループ別・性別別 契約数分布", style={'color': '#1f2937', 'borderBottom': '2px solid #3b82f6', 'paddingBottom': '10px'}),
            dcc.Graph(id='age-gender-distribution')
        ]),

        # **【NEW: キャンセル率分析エリア】**
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.08)'}, children=[
            html.H3("顧客維持（チャーン）分析", style={'color': '#1f2937', 'borderBottom': '2px solid #ef4444', 'paddingBottom': '10px', 'fontWeight': '700'}),
            html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
                # 3. 商品別キャンセル率
                html.Div(style={'width': '50%'}, children=[
                    dcc.Graph(id='product-churn-rate')
                ]),
                # 4. 解約・非解約の年齢分布
                html.Div(style={'width': '50%'}, children=[
                    dcc.Graph(id='age-churn-distribution')
                ]),
            ])
        ]),
    ]),
])


# --- 4. コールバックの定義 (インタラクティブ機能) ---

@app.callback(
    [Output('sales-time-series', 'figure'),
     Output('age-gender-distribution', 'figure'),
     Output('product-churn-rate', 'figure'),    # NEW
     Output('age-churn-distribution', 'figure')], # NEW
    [Input('gender-filter', 'value'),
     Input('product-filter', 'value')]
)
def update_graphs(selected_gender, selected_product):
    """
    フィルターの選択に基づいてグラフを更新するコールバック関数
    """
    
    # データが空の場合は空のグラフを返す
    if df.empty:
        empty_fig = {'layout': {'title': 'データが読み込まれていません', 'xaxis': {'visible': False}, 'yaxis': {'visible': False}}}
        return empty_fig, empty_fig, empty_fig, empty_fig

    # フィルタリング処理
    filtered_df = df.copy()
    
    if selected_gender != 'All':
        filtered_df = filtered_df[filtered_df['Gender'] == selected_gender]
        
    if selected_product != 'All':
        filtered_df = filtered_df[filtered_df['ProductName'] == selected_product]
        
    
    # --- グラフ作成ロジック ---
    
    # 1. 月別総売上推移グラフ
    sales_trend_df = filtered_df.groupby(filtered_df['ContractDate'].dt.to_period('M'))['Price'].sum().reset_index()
    sales_trend_df['ContractDate'] = sales_trend_df['ContractDate'].dt.to_timestamp()
    
    if sales_trend_df.empty:
        time_series_fig = {'layout': {'title': 'フィルター条件に該当するデータがありません'}}
    else:
        time_series_fig = px.line(
            sales_trend_df, x='ContractDate', y='Price', title='月別総売上トレンド',
            labels={'ContractDate': '年月', 'Price': '総売上 (価格の合計)'}, template='plotly_white'
        )
        time_series_fig.update_layout(margin={'l': 60, 'r': 20, 't': 40, 'b': 40}, hovermode='x unified')


    # 2. 年齢グループと性別による契約数分布グラフ
    age_gender_df = filtered_df.groupby(['AgeGroup', 'Gender'], observed=True)['ContractDate'].count().reset_index(name='ContractCount')
    
    if age_gender_df.empty:
        age_gender_fig = {'layout': {'title': 'フィルター条件に該当するデータがありません'}}
    else:
        category_orders = {'AgeGroup': labels}
        age_gender_fig = px.bar(
            age_gender_df, x='AgeGroup', y='ContractCount', color='Gender', barmode='group',
            category_orders=category_orders, title='年齢グループ別・性別別 契約件数',
            labels={'AgeGroup': '年齢グループ', 'ContractCount': '契約数', 'Gender': '性別'}, template='plotly_white'
        )
        age_gender_fig.update_layout(margin={'t': 40, 'b': 20, 'l': 40, 'r': 20})
        
        
    # **【NEW: 3. 商品別キャンセル率グラフの作成】**
    if filtered_df.empty or filtered_df['ProductName'].nunique() == 0:
        product_churn_fig = {'layout': {'title': 'フィルター条件に該当するデータがありません'}}
    else:
        # 商品ごとに総契約数とキャンセル数を集計
        churn_summary = filtered_df.groupby('ProductName').agg(
            TotalContracts=('ContractDate', 'count'),
            Cancellations=('IsCancelled', 'sum')
        ).reset_index()

        # キャンセル率を計算
        churn_summary['ChurnRate'] = (churn_summary['Cancellations'] / churn_summary['TotalContracts']) * 100
        
        product_churn_fig = px.bar(
            churn_summary.sort_values('ChurnRate', ascending=False),
            x='ProductName', 
            y='ChurnRate', 
            color='ChurnRate',
            color_continuous_scale=px.colors.sequential.Reds, # キャンセル率が高いほど赤く
            title='商品別キャンセル率 (Churn Rate)',
            labels={'ProductName': '商品名', 'ChurnRate': 'キャンセル率 (%)'}, 
            template='plotly_white'
        )
        product_churn_fig.update_layout(
            margin={'t': 40, 'b': 20, 'l': 40, 'r': 20},
            yaxis={'tickformat': '.1f'} # 1桁の小数点で表示
        )
        
    # **【NEW: 4. 解約・非解約の年齢分布比較グラフの作成】**
    if filtered_df.empty:
        age_churn_fig = {'layout': {'title': 'フィルター条件に該当するデータがありません'}}
    else:
        # IsCancelled (キャンセル済み/未キャンセル) ごとに年齢分布をヒストグラムで比較
        age_churn_fig = px.histogram(
            filtered_df,
            x='Age', 
            color='IsCancelled',
            barmode='overlay',
            histnorm='percent', # 全体に対する割合で表示
            title='解約有無別 年齢分布',
            labels={'Age': '年齢', 'IsCancelled': 'キャンセル済み', 'count': '割合 (%)'},
            category_orders={'IsCancelled': [False, True]},
            opacity=0.6,
            template='plotly_white'
        )
        # 凡例のテキストを日本語に修正
        age_churn_fig.for_each_trace(lambda t: t.update(name=t.name.replace('True', 'キャンセル済み').replace('False', '未キャンセル')))
        age_churn_fig.update_layout(
            margin={'t': 40, 'b': 20, 'l': 40, 'r': 20},
            yaxis={'tickformat': '.0f'} # 整数で表示
        )
        
    return time_series_fig, age_gender_fig, product_churn_fig, age_churn_fig


# --- 5. アプリケーションの実行 ---
if __name__ == '__main__':
    # 新しいDashの実行コマンド
    app.run(debug=True)
