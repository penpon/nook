def create_layout(app_state):
    # ... 既存コード ...
    
    # サイドバー部分を修正
    with ui.left_drawer().classes("bg-gray-800 text-white"):
        # トップのapp/dashboardメニューを削除するためのCSS
        ui.add_head_html("""
        <style>
        .nicegui-sidebar-nav {
            display: none !important;
        }
        </style>
        """)
        
        ui.label("Nook").classes("text-2xl font-bold")
        ui.label("パーソナル情報ハブ").classes("text-sm text-gray-400")
        
        # 情報ソースと日付のセクションはそのまま維持
        with ui.card().classes("w-full"):
            ui.label("情報ソース").classes("text-sm text-gray-400")
            # ... 既存コード ...
            
        with ui.card().classes("w-full"):
            ui.label("日付").classes("text-sm text-gray-400")
            # ... 既存コード ...
        
        # 天気情報の表示を削除
    
    # ... 既存コード ... 