import streamlit as st
import random
from pyvis.network import Network
import streamlit.components.v1 as components

# --- 1. 定数と初期データ定義 ---
COUNTRIES = ["プレイヤー(赤)", "AI(青)", "AI(緑)", "中立"]
COLORS = {"プレイヤー(赤)": "#ff4b4b", "AI(青)": "#1c83e1", "AI(緑)": "#00f060", "中立": "#aaaaaa"}

# 隊長リストのデータベース
CAPTAIN_POOL = [
    {"name": "レオニダス", "atk": 15, "dfn": 10, "mot": 5},
    {"name": "ジャンヌ", "atk": 10, "dfn": 15, "mot": 8},
    {"name": "オダ・ノブナガ", "atk": 18, "dfn": 8, "mot": 4},
    {"name": "アーサー", "atk": 12, "dfn": 12, "mot": 6},
    {"name": "アレクサンダー", "atk": 14, "dfn": 11, "mot": 7},
]

# --- 2. セッション状態の初期化 ---
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.phase = "資金確保"
    st.session_state.turn = 1
    
    # 国家ごとの資金・雇用済みの隊長
    st.session_state.country_data = {
        "プレイヤー(赤)": {"gold": 100, "captains": []},
        "AI(青)": {"gold": 100, "captains": [{"name": "AI将軍A", "atk": 10, "dfn": 10, "mot": 5}]},
        "AI(緑)": {"gold": 100, "captains": [{"name": "AI将軍B", "atk": 10, "dfn": 10, "mot": 5}]},
    }
    
    # 40ノードの生成（スケールフリーネットワーク風に複雑に接続）
    num_nodes = 40
    nodes = {}
    
    # 初期配置（最初の3つを各大国、残りを中立）
    for i in range(num_nodes):
        node_id = f"領地_{i+1}"
        if i == 0: owner = "プレイヤー(赤)"
        elif i == 1: owner = "AI(青)"
        elif i == 2: owner = "AI(緑)"
        else: owner = "中立"
        
        nodes[node_id] = {
            "owner": owner,
            "economy": random.randint(10, 50), # 経済力（初期ランダム）
            "troops": random.randint(5, 15) if owner != "中立" else random.randint(1, 5),
            "adjacent": set()
        }
    
    # 複雑なつながり（エッジ）の生成
    node_keys = list(nodes.keys())
    # 最低限の連結性を確保（1直線につなぐ）
    for i in range(num_nodes - 1):
        nodes[node_keys[i]]["adjacent"].add(node_keys[i+1])
        nodes[node_keys[i+1]]["adjacent"].add(node_keys[i])
    
    # ランダムな追加のつながりを作って複雑化
    for _ in range(50):
        n1 = random.choice(node_keys)
        n2 = random.choice(node_keys)
        if n1 != n2:
            nodes[n1]["adjacent"].add(n2)
            nodes[n2]["adjacent"].add(n1)
            
    # set型はそのまま扱いにくいのでlistに変換
    for n in nodes:
        nodes[n]["adjacent"] = list(nodes[n]["adjacent"])
        
    st.session_state.nodes = nodes
    st.session_state.log = ["ゲームが開始されました。"]
    st.session_state.current_candidate = random.choice(CAPTAIN_POOL) # 最初の雇用候補

# --- 3. ゲームロジック用関数 ---
def add_log(text):
    st.session_state.log.insert(0, f"【ターン{st.session_state.turn}】{text}")

def draw_map():
    """Pyvisを使用したネットワークマップの描画"""
    net = Network(height="400px", width="100%", bgcolor="#222222", font_color="white")
    
    for node_id, info in st.session_state.nodes.items():
        color = COLORS[info["owner"]]
        label = f"{node_id}\n(兵:{info['troops']}/経:{info['economy']})"
        net.add_node(node_id, label=label, color=color, size=20)
        
    for node_id, info in st.session_state.nodes.items():
        for adj in info["adjacent"]:
            # 重複描画を避けるためID比較
            if node_id < adj:
                net.add_edge(node_id, adj, color="#555555")
                
    net.toggle_physics(True)
    net.save_graph("map.html")
    
    # HTMLとしてStreamlitに埋め込み
    with open("map.html", 'r', encoding='utf-8') as f:
        html_data = f.read()
    components.html(html_data, height=410)

# --- 4. UI・画面表示部 ---
st.title("🌐 ノード奪還戦：🗺️ 40ノード大戦国")

# レイアウトを2列に分割（左：マップと操作、右：ステータスとログ）
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"現在のフェーズ: 【{st.session_state.phase}】")
    draw_map()

with col2:
    st.subheader("📊 国家ステータス")
    p_gold = st.session_state.country_data["プレイヤー(赤)"]["gold"]
    p_caps = [c["name"] for c in st.session_state.country_data["プレイヤー(赤)"]["captains"]]
    st.metric("領有資金額 (G)", f"{p_gold} G")
    st.write(f"**配下の隊長:** {', '.join(p_caps) if p_caps else 'なし'}")
    
    st.subheader("📜 戦況履歴")
    st.caption("\n".join(st.session_state.log[:8]))

# --- 5. フェーズごとの処理UI ---
st.divider()

if st.session_state.phase == "資金確保":
    st.info("【資金確保フェーズ】領地の経済力に応じて資金を獲得します。")
    if st.button("資金を回収して次へ"):
        # プレイヤーとAIの資金回収
        for country in st.session_state.country_data:
            earned = sum(n["economy"] for n in st.session_state.nodes.values() if n["owner"] == country)
            st.session_state.country_data[country]["gold"] += earned
            if country == "プレイヤー(赤)":
                add_log(f"領地から {earned} G の資金を確保しました。")
        st.session_state.phase = "内政"
        st.rerun()

elif st.session_state.phase == "内政":
    st.info("【内政フェーズ】資金を50G消費して、プレイヤー領地1つの経済力を+20できます。")
    player_nodes = [k for k, v in st.session_state.nodes.items() if v["owner"] == "プレイヤー(赤)"]
    
    selected_node = st.selectbox("投資する領地を選択:", player_nodes)
    col_inv, col_skip = st.columns(2)
    
    if col_inv.button("💰 50G投資する (経済力+20)"):
        if st.session_state.country_data["プレイヤー(赤)"]["gold"] >= 50:
            st.session_state.country_data["プレイヤー(赤)"]["gold"] -= 50
            st.session_state.nodes[selected_node]["economy"] += 20
            add_log(f"{selected_node} に投資し、経済力が向上しました。")
            st.session_state.phase = "部隊確保"
            st.session_state.current_candidate = random.choice(CAPTAIN_POOL) # 次の雇用候補決定
            st.rerun()
        else:
            st.error("資金が足りません！")
            
    if col_skip.button("内政をスキップして次へ"):
        st.session_state.phase = "部隊確保"
        st.session_state.current_candidate = random.choice(CAPTAIN_POOL)
        st.rerun()

elif st.session_state.phase == "部隊確保":
    st.info("【部隊確保フェーズ】新しく隊長を雇用するか選択します（一律 60 G）。")
    cand = st.session_state.current_candidate
    
    st.markdown(f"""
    **【仕官を求めてきた隊長】**
    *   **名前:** {cand['name']}
    *   **基礎攻撃力:** {cand['atk']} / **防御力:** {cand['dfn']}
    *   **やる気（攻撃加算値）:** +{cand['mot']}
    """)
    
    col_hire, col_pass = st.columns(2)
    if col_hire.button(f"🤝 {cand['name']}を雇う (60G)"):
        if st.session_state.country_data["プレイヤー(赤)"]["gold"] >= 60:
            st.session_state.country_data["プレイヤー(赤)"]["gold"] -= 60
            st.session_state.country_data["プレイヤー(赤)"]["captains"].append(cand)
            add_log(f"隊長「{cand['name']}」が配下に加わりました。")
            st.session_state.phase = "部隊配置"
            st.rerun()
        else:
            st.error("資金が足りません！")
            
    if col_pass.button("見送る（次へ）"):
        add_log("隊長の雇用を見送りました。")
        st.session_state.phase = "部隊配置"
        st.rerun()

elif st.session_state.phase == "部隊配置":
    st.info("【部隊配置フェーズ】資金を消費して、領地に兵力を補強します（1兵力 = 2G）。")
    player_nodes = [k for k, v in st.session_state.nodes.items() if v["owner"] == "プレイヤー(赤)"]
    
    target_node = st.selectbox("兵力を送る領地:", player_nodes)
    max_affordable = st.session_state.country_data["プレイヤー(赤)"]["gold"] // 2
    amount = st.number_input("配備する兵力数:", min_value=0, max_value=max_affordable, value=0)
    
    if st.button("🪖 兵力を配備して次へ"):
        if amount > 0:
            st.session_state.country_data["プレイヤー(赤)"]["gold"] -= (amount * 2)
            st.session_state.nodes[target_node]["troops"] += amount
            add_log(f"{target_node} に兵力を {amount} 補充しました。")
        st.session_state.phase = "侵攻"
        st.rerun()

elif st.session_state.phase == "侵攻":
    st.info("【侵攻フェーズ】隣接する敵地、または中立地に攻め込みます。")
    
    # プレイヤーが攻め込める（隣接に敵・中立がある）領地を抽出
    atk_sources = []
    for node_id, info in st.session_state.nodes.items():
        if info["owner"] == "プレイヤー(赤)" and info["troops"] > 1:
            # 隣接に自分以外の領地があるか
            has_enemy_neighbor = any(st.session_state.nodes[adj]["owner"] != "プレイヤー(赤)" for adj in info["adjacent"])
            if has_enemy_neighbor:
                atk_sources.append(node_id)
                
    if not atk_sources:
        st.warning("現在、攻撃を仕掛けられる隣接領地がないか、兵力が不足しています（攻めるには2以上の兵力が必要）。")
        if st.button("侵攻せずターン終了（AIの行動へ）"):
            st.session_state.phase = "資金確保"
            st.session_state.turn += 1
            st.rerun()
    else:
        src_node = st.selectbox("出撃元領地を選択:", atk_sources)
        # 選択した出撃元から攻め込める隣接領地リスト
        possible_targets = [adj for adj in st.session_state.nodes[src_node]["adjacent"] if st.session_state.nodes[adj]["owner"] != "プレイヤー(赤)"]
        tgt_node = st.selectbox("攻撃先領地を選択:", possible_targets)
        
        # 出撃させる兵力（元の領地に最低1残す）
        max_atk_troops = st.session_state.nodes[src_node]["troops"] - 1
        atk_troops = st.slider("出撃兵力数", min_value=1, max_value=max_atk_troops, value=max_atk_troops)
        
        if st.button("⚔️ 侵攻開始！"):
            # 戦闘計算（簡易版：隊長の能力を反映）
            # プレイヤーの攻撃力 = 出撃兵力 + 隊長全員の (攻撃力 + やる気) の平均
            p_caps = st.session_state.country_data["プレイヤー(赤)"]["captains"]
            cap_atk_bonus = sum(c["atk"] + c["mot"] for c in p_caps) // len(p_caps) if p_caps else 0
            total_atk = atk_troops + cap_atk_bonus + random.randint(1, 10)
            
            # 防衛側の防御力
            def_info = st.session_state.nodes[tgt_node]
            total_dfn = def_info["troops"] + random.randint(1, 10)
            
            if total_atk > total_dfn:
                # 勝利：領地を奪う。残存兵力が新しい領地の兵力に
                survivors = max(1, atk_troops - (total_dfn // 2))
                st.session_state.nodes[src_node]["troops"] -= atk_troops
                st.session_state.nodes[tgt_node]["owner"] = "プレイヤー(赤)"
                st.session_state.nodes[tgt_node]["troops"] = survivors
                add_log(f"【勝利】{src_node}から{tgt_node}へ侵攻成功！占領しました。")
            else:
                # 敗北：出撃部隊の全滅、防衛側も少し減る
                st.session_state.nodes[src_node]["troops"] -= atk_troops
                st.session_state.nodes[tgt_node]["troops"] = max(1, def_info["troops"] - (atk_troops // 2))
                add_log(f"【敗北】{tgt_node} の防衛線に阻まれ、部隊が壊滅しました。")
                
            # AIのターン擬似処理（簡易的に中立やプレイヤーをランダムに襲う等を入れるとさらに良くなります）
            # 今回はシンプルにフェーズを戻してターンを進める
            st.session_state.phase = "資金確保"
            st.session_state.turn += 1
            st.rerun()