import streamlit as st
import random
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile
import os

st.set_page_config(layout="wide")

# --- 1. 定数と初期データ定義 ---
COUNTRIES = ["プレイヤー(赤)", "AI(青)", "AI(緑)", "中立"]
COLORS = {"プレイヤー(赤)": "#ff4b4b", "AI(青)": "#1c83e1", "AI(緑)": "#00f060", "中立": "#aaaaaa"}

# 【新仕様】5大兵種のマスターデータ
SOLDIER_TYPES = {
    "銃撃部隊": {"cost": 10, "atk": 5, "range": 150},
    "砲撃部隊": {"cost": 25, "atk": 12, "range": 300},
    "戦車部隊": {"cost": 50, "atk": 25, "range": 450},
    "戦闘機部隊": {"cost": 90, "atk": 50, "range": 600},
    "ミサイル部隊": {"cost": 150, "atk": 90, "range": 800},
}

CAPTAIN_POOL = [
    {"name": "レオニダス", "atk": 15, "dfn": 10, "mot": 5},
    {"name": "ジャンヌ", "atk": 10, "dfn": 15, "mot": 8},
    {"name": "オダ・ノブナガ", "atk": 18, "dfn": 8, "mot": 4},
    {"name": "アーサー", "atk": 12, "dfn": 12, "mot": 6},
    {"name": "アレクサンダー", "atk": 14, "dfn": 11, "mot": 7},
]

# --- 2. セッション状態の初期化 ---
if "map_generated" not in st.session_state:
    st.session_state.map_generated = True
    st.session_state.phase = "資金確保"
    st.session_state.turn = 1
    
    st.session_state.country_data = {
        "プレイヤー(赤)": {"gold": 400, "captains": []}, # 兵を雇うために初期資金を多めに設定
        "AI(青)": {"gold": 300, "captains": []},
        "AI(緑)": {"gold": 300, "captains": []},
    }
    
    # 【新仕様】全部隊の集中管理辞書
    # 構造: "部隊名": {"owner": 国家, "captain": 隊長データ, "soldier_type": 兵種, "count": 兵数, "location": 領地ID}
    st.session_state.units = {}
    
    # 初期AI部隊を1つずつ配備
    st.session_state.units["AI青軍第1部隊"] = {
        "owner": "AI(青)", "captain": {"name": "AI将軍A", "atk": 10, "dfn": 10, "mot": 5},
        "soldier_type": "砲撃部隊", "count": 4, "location": "領地_2"
    }
    st.session_state.units["AI緑軍第1部隊"] = {
        "owner": "AI(緑)", "captain": {"name": "AI将軍B", "atk": 10, "dfn": 10, "mot": 5},
        "soldier_type": "銃撃部隊", "count": 10, "location": "領地_3"
    }

    num_nodes = 40
    nodes = {}
    for i in range(num_nodes):
        node_id = f"領地_{i+1}"
        if i == 0: owner = "プレイヤー(赤)"
        elif i == 1: owner = "AI(青)"
        elif i == 2: owner = "AI(緑)"
        else: owner = "中立"
        
        nodes[node_id] = {
            "owner": owner,
            "economy": random.randint(15, 40),
            "adjacent": set()
        }
    
    node_keys = list(nodes.keys())
    for i in range(num_nodes - 1):
        nodes[node_keys[i]]["adjacent"].add(node_keys[i+1])
        nodes[node_keys[i+1]]["adjacent"].add(node_keys[i])
    
    random.seed(42)
    for _ in range(50):
        n1 = random.choice(node_keys)
        n2 = random.choice(node_keys)
        if n1 != n2:
            nodes[n1]["adjacent"].add(n2)
            nodes[n2]["adjacent"].add(n1)
            
    for n in nodes:
        nodes[n]["adjacent"] = list(nodes[n]["adjacent"])
        
    st.session_state.nodes = nodes
    st.session_state.log = ["新世界が定義されました。隊長を率いて出撃せよ！"]
    st.session_state.current_candidate = random.choice(CAPTAIN_POOL)
# --- AIの侵攻処理関数 ---
def run_ai_turn():
    """【新仕様】青国と緑国がそれぞれ自分の『部隊』を隣接する他国・中立の領地へランダムに移動・侵攻させる"""
    # ループ内で辞書が変更されるのを防ぐため、コピーを作成してループ
    all_units = list(st.session_state.units.items())
    
    for unit_name, u_info in all_units:
        # AI国家の部隊だけを処理
        if u_info["owner"] in ["AI(青)", "AI(緑)"]:
            ai_country = u_info["owner"]
            current_loc = u_info["location"]
            
            # 兵数が1以下の部隊は動かさない（安全のため）
            if u_info["count"] <= 1:
                continue
                
            # その部隊がいる領地から、隣接する領地を取得
            possible_targets = st.session_state.nodes[current_loc]["adjacent"]
            # 自分以外の領地、または中立の領地を優先してターゲットにする
            enemy_targets = [adj for adj in possible_targets if st.session_state.nodes[adj]["owner"] != ai_country]
            
            # もし周りが全部自分の領地なら、通常の隣接領地を移動先にする
            dest_targets = enemy_targets if enemy_targets else possible_targets
            
            if not dest_targets:
                continue
                
            # ランダムに1つの移動先を決定
            tgt_node = random.choice(dest_targets)
            dest_owner = st.session_state.nodes[tgt_node]["owner"]
            
            # 部隊の位置を書き換え（移動）
            st.session_state.units[unit_name]["location"] = tgt_node
            
            # 移動先が他国または中立の場合、その領地を占領（※ステップ1用の簡易戦闘）
            if dest_owner != ai_country:
                st.session_state.nodes[tgt_node]["owner"] = ai_country
                add_log(f"⚔️ 凶報: {ai_country}の「{unit_name}」が {tgt_node}(元:{dest_owner}) へ侵攻し、領地を奪いました！")
# --- 3. 共通関数 ---
def add_log(text):
    st.session_state.log.insert(0, f"【T{st.session_state.turn}】{text}")

def generate_improved_node_label(node_id, info):
    owner = info["owner"]
    owner_icon = "👤" if owner == "プレイヤー(赤)" else "🤖" if owner.startswith("AI") else "🏳️"
    
    # 【新仕様】その領地にいる部隊を検索してラベルに表示
    staying_units = [u_name for u_name, u_info in st.session_state.units.items() if u_info["location"] == node_id]
    
    unit_text = ""
    if staying_units:
        unit_details = []
        for uname in staying_units:
            u = st.session_state.units[uname]
            unit_details.append(f"[{u['captain']['name']}]")
        unit_text = "\n" + "\n".join(unit_details)
    else:
        unit_text = "\n(部隊なし)"
        
    return f"{node_id}\n{owner_icon}\n{unit_text}"

def generate_hover_title(node_id, info):
    staying_units = [u_name for u_name, u_info in st.session_state.units.items() if u_info["location"] == node_id]
    unit_logs = ""
    for uname in staying_units:
        u = st.session_state.units[uname]
        unit_logs += f"・{uname} ({u['soldier_type']} × {u['count']})\n"
        
    return (
        f"【{node_id}】\n"
        f"支配国家: {info['owner']}\n"
        f"経済力: {info['economy']} G\n"
        f"--- 駐留部隊 ---\n{unit_logs if unit_logs else 'なし'}"
    )

def draw_map_improved():
    net = Network(height="480px", width="100%", bgcolor="#222222", font_color="white")
    
    for node_id, info in st.session_state.nodes.items():
        color = COLORS[info["owner"]]
        label = generate_improved_node_label(node_id, info)
        title = generate_hover_title(node_id, info)
        
        # 領地内の総兵力に応じてノードサイズを可変に
        staying_units = [u for u in st.session_state.units.values() if u["location"] == node_id]
        total_troops = sum(u["count"] for u in staying_units)
        size = 25 + min(20, total_troops * 2) # 兵数に応じてノードが大きくなるよう調整
        
        is_frontline = any(st.session_state.nodes[adj]["owner"] != info["owner"] for adj in info["adjacent"])
        if is_frontline and info["owner"] == "プレイヤー(赤)":
            border_width = 5
            border_color = "#ffff00"
        else:
            border_width = 1
            border_color = color
        
        net.add_node(
            node_id, label=label, size=size, title=title, shape="circle", 
            borderWidth=border_width, color=dict(border=border_color, background=color),
            font=dict(size=13, color="white", strokeWidth=2, strokeColor="#000000")
        )
        
    for node_id, info in st.session_state.nodes.items():
        for adj in info["adjacent"]:
            if node_id < adj:
                net.add_edge(node_id, adj, color="#555555", width=2)
                
    net.toggle_physics(False) 
    net.set_options('{"interaction": {"hover": true}, "nodes": {"font": {"face": "monospace"}}}')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "map.html")
        net.save_graph(path)
        with open(path, 'r', encoding='utf-8') as f:
            html_data = f.read()
    components.html(html_data, height=490)
# --- 4. 画面表示レイアウト ---
st.title("🌐 ノード奪還戦：🗺️ 40ノード大戦国 (兵種・部隊改造版)")

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader(f"ターン: {st.session_state.turn} | 現在のフェーズ: 【{st.session_state.phase}】")
    draw_map_improved()

with col2:
    st.subheader("📊 プレイヤー情報")
    p_gold = st.session_state.country_data["プレイヤー(赤)"]["gold"]
    p_caps = [c["name"] for c in st.session_state.country_data["プレイヤー(赤)"]["captains"]]
    
    # 待機中（部隊を持っていない）の隊長リスト
    busy_caps = [u["captain"]["name"] for u in st.session_state.units.values() if u["owner"] == "プレイヤー(赤)"]
    free_caps = [c for c in p_caps if c not in busy_caps]
    
    st.metric("所持金 (G)", f"{p_gold} G")
    st.write(f"**全配下の隊長:** {', '.join(p_caps) if p_caps else 'なし'}")
    st.write(f"**未配属の隊長:** {', '.join(free_caps) if free_caps else 'なし（部隊配置で兵を配属してください）'}")
    
    st.subheader("📜 戦況履歴")
    st.caption("\n".join(st.session_state.log[:8]))

st.divider()

# --- 5. フェーズ管理UI ---
if st.session_state.phase == "資金確保":
    st.info("【資金確保フェーズ】領地の経済力に応じて資金を獲得します。")
    if st.button("💰 資金を回収して内政へ"):
        for country in st.session_state.country_data:
            earned = sum(n["economy"] for n in st.session_state.nodes.values() if n["owner"] == country)
            st.session_state.country_data[country]["gold"] += earned
            if country == "プレイヤー(赤)":
                add_log(f"領地から {earned} G の資金を回収しました。")
        st.session_state.phase = "内政"
        st.rerun()

elif st.session_state.phase == "内政":
    st.info("【内政フェーズ】50Gを支払い、選択した領地の経済力を+20します。")
    player_nodes = [k for k, v in st.session_state.nodes.items() if v["owner"] == "プレイヤー(赤)"]
    
    if player_nodes:
        selected_node = st.selectbox("投資する領地:", player_nodes)
        col_inv, col_skip = st.columns(2)
        if col_inv.button("💸 50G投資する"):
            if st.session_state.country_data["プレイヤー(赤)"]["gold"] >= 50:
                st.session_state.country_data["プレイヤー(赤)"]["gold"] -= 50
                st.session_state.nodes[selected_node]["economy"] += 20
                add_log(f"{selected_node} に投資し、経済力が向上しました。")
                st.session_state.phase = "部隊確保"
                st.session_state.current_candidate = random.choice(CAPTAIN_POOL)
                st.rerun()
            else:
                st.error("資金が足りません！")
        if col_skip.button("内政をスキップ"):
            st.session_state.phase = "部隊確保"
            st.session_state.current_candidate = random.choice(CAPTAIN_POOL)
            st.rerun()
    else:
        st.error("領地がありません。ゲームオーバーです。")

elif st.session_state.phase == "部隊確保":
    st.info("【部隊確保フェーズ】隊長を1名雇用できます（一律 60 G）。")
    cand = st.session_state.current_candidate
    st.markdown(f"**仕官希望者:** {cand['name']} (攻撃:{cand['atk']} / 防御:{cand['dfn']} / やる気:+{cand['mot']})")
    
    col_hire, col_pass = st.columns(2)
    if col_hire.button(f"🤝 雇用する (60G)"):
        if st.session_state.country_data["プレイヤー(赤)"]["gold"] >= 60:
            if cand in st.session_state.country_data["プレイヤー(赤)"]["captains"]:
                st.warning("この隊長は既に雇用しています。")
            else:
                st.session_state.country_data["プレイヤー(赤)"]["gold"] -= 60
                st.session_state.country_data["プレイヤー(赤)"]["captains"].append(cand)
                add_log(f"隊長「{cand['name']}」が配下に加わりました。")
                st.session_state.phase = "部隊配置"
                st.rerun()
        else:
            st.error("資金が足りません！")
    if col_pass.button("見送る"):
        st.session_state.phase = "部隊配置"
        st.rerun()

elif st.session_state.phase == "部隊配置":
    st.info("【部隊配置フェーズ】未配属の隊長に兵種と兵力を与え、「部隊」を結成します。")
    
    if not free_caps:
        st.warning("現在、新しく結成できる未配属の隊長がいません。部隊配置を終了します。")
        if st.button("侵攻フェーズへ進む"):
            st.session_state.phase = "侵攻"
            st.rerun()
    else:
        # 1. 隊長の選択
        selected_cap_name = st.selectbox("兵を配属する隊長を選択:", free_caps)
        selected_cap_data = next(c for c in st.session_state.country_data["プレイヤー(赤)"]["captains"] if c["name"] == selected_cap_name)
        
        # 2. 兵種の選択
        st.write("--- 兵種カタログ ---")
        st.table([{"兵種": k, "コスト(1機辺り)": f"{v['cost']}G", "攻撃力": v["atk"], "射程": v["range"]} for k, v in SOLDIER_TYPES.items()])
        selected_soldier = st.selectbox("編成する兵種を選択:", list(SOLDIER_TYPES.keys()))
        
        # 3. 兵数の決定（買える上限を計算）
        unit_cost = SOLDIER_TYPES[selected_soldier]["cost"]
        max_buy = st.session_state.country_data["プレイヤー(赤)"]["gold"] // unit_cost
        
        if max_buy == 0:
            st.error(f"資金が足りないため、{selected_soldier} を雇うことができません！")
        else:
            troop_count = st.slider(f"編成する兵数 (1機 {unit_cost}G):", min_value=1, max_value=max_buy, value=1)
            total_spend = troop_count * unit_cost
            
            # 4. 配置する初期領地の選択（プレイヤー領地のみ）
            player_nodes = [k for k, v in st.session_state.nodes.items() if v["owner"] == "プレイヤー(赤)"]
            deploy_node = st.selectbox("初期配置する領地:", player_nodes)
            
            if st.button(f"🪖 {selected_cap_name}部隊を結成 (総額: {total_spend}G)"):
                # 資金消費
                st.session_state.country_data["プレイヤー(赤)"]["gold"] -= total_spend
                
                # 新しい部隊をグローバルな部隊データに追加
                unit_id = f"{selected_cap_name}部隊"
                st.session_state.units[unit_id] = {
                    "owner": "プレイヤー(赤)",
                    "captain": selected_cap_data,
                    "soldier_type": selected_soldier,
                    "count": troop_count,
                    "location": deploy_node
                }
                
                add_log(f"【部隊結成】{selected_cap_name}が{selected_soldier}×{troop_count}を率いて{deploy_node}に配備されました。")
                st.rerun()
                
        if st.button("配置を終了して侵攻フェーズへ"):
            st.session_state.phase = "侵攻"
            st.rerun()




elif st.session_state.phase == "侵攻":
    st.info("【侵攻フェーズ】自分の部隊を選択し、隣接する領地へ移動・侵攻させます。")
    
    # 1. プレイヤーが動かせる「自分の部隊」をリストアップ
    player_units = {u_name: u_info for u_name, u_info in st.session_state.units.items() if u_info["owner"] == "プレイヤー(赤)"}
    
    if not player_units:
        st.warning("現在、動かせる部隊がありません。部隊配置フェーズで部隊を結成してください。")
        if st.button("🏁 行動せずにターン終了（次ターンへ）"):
            st.session_state.phase = "資金確保"
            st.session_state.turn += 1
            st.rerun()
    else:
        # 部隊の選択
        selected_unit_name = st.selectbox("動かす部隊を選択してください:", list(player_units.keys()))
        unit_info = player_units[selected_unit_name]
        current_loc = unit_info["location"]
        
        st.write(f"現在の位置: **{current_loc}** ({unit_info['soldier_type']} × {unit_info['count']})")
        
        # 2. その部隊がいる領地から「移動可能な隣接領地」を取得
        possible_destinations = st.session_state.nodes[current_loc]["adjacent"]
        target_loc = st.selectbox("移動・侵攻先の領地を選択してください:", possible_destinations)
        
        dest_owner = st.session_state.nodes[target_loc]["owner"]
        st.write(f"目的地の所有者: **{dest_owner}**")
        
        if st.button("🚀 部隊を移動 / 侵攻開始"):
            # 部隊の位置を書き換える（これが移動の実装になります！）
            st.session_state.units[selected_unit_name]["location"] = target_loc
            
            # 移動先が中立または無人の場合（ステップ1の暫定処理）
            if dest_owner != "プレイヤー(赤)":
                # 領地の支配権をプレイヤーに変更
                st.session_state.nodes[target_loc]["owner"] = "プレイヤー(赤)"
                add_log(f"【進軍】{selected_unit_name}が{current_loc}から{target_loc}へ移動し、領地を確保しました！")
            else:
                add_log(f"【移動】{selected_unit_name}が{current_loc}から同盟領地の{target_loc}へ移動しました。")
                
                # プレイヤー行動後にAIが行動
                run_ai_turn()
                st.session_state.phase = "資金確保"
                st.session_state.turn += 1
                st.rerun()
        else:
            st.write("攻め込める隣接領地がありません。")
            
    
        if st.button("🏁 この部隊は動かさずにターン終了"):
            run_ai_turn()
            st.session_state.phase = "資金確保"
            st.session_state.turn += 1
            st.rerun()