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

# 【兵種マスター】コスト・攻撃力・射程（Canvas上のピクセル数）
SOLDIER_TYPES = {
    "銃撃部隊": {"cost": 10, "atk": 5, "range": 180, "color": "#ffdd67"},
    "砲撃部隊": {"cost": 25, "atk": 12, "range": 320, "color": "#ff9f43"},
    "戦車部隊": {"cost": 50, "atk": 25, "range": 480, "color": "#10ac84"},
    "戦闘機部隊": {"cost": 90, "atk": 50, "range": 650, "color": "#0abde3"},
    "ミサイル部隊": {"cost": 150, "atk": 90, "range": 850, "color": "#ee5253"},
}

CAPTAIN_POOL = [
    {"name": "レオニダス", "atk": 15, "dfn": 10, "mot": 5, "image": "assets/reonidas.png"},
    {"name": "ジャンヌ", "atk": 10, "dfn": 15, "mot": 8, "image": "assets/zannu.png"},
    {"name": "ノブナガ", "atk": 18, "dfn": 8, "mot": 4, "image": "assets/nobunaga.png"},
    {"name": "アーサー", "atk": 12, "dfn": 12, "mot": 6, "image": "assets/arther.png"},
    {"name": "アレクサンダー", "atk": 14, "dfn": 11, "mot": 7, "image": "assets/arexander.png"},
    {"name": "あかね", "atk": 13, "dfn": 14, "mot": 10, "image": "assets/akane.png"},
    {"name": "しずく", "atk": 16, "dfn": 16, "mot": 12, "image": "assets/sizuku.png"},
    {"name": "みつば", "atk": 12, "dfn": 18, "mot": 13, "image": "assets/mituba.png"},
    {"name": "あいり", "atk": 17, "dfn": 12, "mot": 5, "image": "assets/airi.png"},
]
# --- AI専用の出撃待ち部隊プール ---
AI_UNIT_POOL = [
    {"captain": {"name": "ゼウス", "atk": 20, "dfn": 15, "image": "assets/zeusu.png"}, "soldier_type": "ミサイル部隊", "count": 3},
    {"captain": {"name": "カエサル", "atk": 12, "dfn": 18, "image": "assets/kaesaru.png"}, "soldier_type": "戦車部隊", "count": 5},
    {"captain": {"name": "ナポレオン", "atk": 16, "dfn": 10, "image": "assets/naporeon.png"}, "soldier_type": "砲撃部隊", "count": 8},
    {"captain": {"name": "ハンニバル", "atk": 15, "dfn": 12, "image": "assets/hannibaru.png"}, "soldier_type": "戦闘機部隊", "count": 4},
    {"captain": {"name": "チンギスハーン", "atk": 14, "dfn": 8, "image": "assets/tingishun.png"}, "soldier_type": "銃撃部隊", "count": 15},
    {"captain": {"name": "シバ", "atk": 10, "dfn": 10, "image": "assets/siba.png"}, "soldier_type": "銃撃部隊", "count": 10},
]
# --- 2. セッション状態の初期化 ---
if "map_generated" not in st.session_state:
    st.session_state.map_generated = True
    st.session_state.phase = "資金確保"
    st.session_state.turn = 1
    
    st.session_state.country_data = {
        "プレイヤー(赤)": {"gold": 500, "captains": []},
        "AI(青)": {"gold": 300, "captains": []},
        "AI(緑)": {"gold": 300, "captains": []},
    }
    
    st.session_state.units = {}
    
    # 初期AI部隊の配備
    st.session_state.units["AI青軍第1部隊"] = {
        "owner": "AI(青)", "captain": {"name": "AI将軍A", "atk": 10, "dfn": 10, "mot": 5, "image": "assets/aia.png"},
        "soldier_type": "砲撃部隊", "count": 6, "location": "領地_4", "moved": False
    }
    st.session_state.units["AI緑軍第1部隊"] = {
        "owner": "AI(緑)", "captain": {"name": "AI将軍B", "atk": 10, "dfn": 10, "mot": 5, "image": "assets/aib.png"},
        "soldier_type": "銃撃部隊", "count": 12, "location": "領地_7", "moved": False
    }

    # 戦闘結果をJavaScriptから受け取るためのトリガー変数
    st.session_state.battle_result = None
    st.session_state.active_battle = {}

    num_nodes = 40
    nodes = {}
    for i in range(num_nodes):
        node_id = f"領地_{i+1}"
        if i == 0: owner = "プレイヤー(赤)"
        elif i == 3: owner = "AI(青)"
        elif i == 6: owner = "AI(緑)"
        else: owner = "中立"
        
        nodes[node_id] = {
            "owner": owner, "economy": random.randint(15, 40), "adjacent": set()
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
    st.session_state.log = ["新世界が定義されました。部隊を結成して出撃せよ！"]
    st.session_state.current_candidate = random.choice(CAPTAIN_POOL)

# --- 3. 共通ロジック ---
def add_log(text):
    st.session_state.log.insert(0, f"【T{st.session_state.turn}】{text}")

def run_ai_turn():
    """【AI専用リスト出撃版】青国と緑国が、専用プールからランダムに部隊を編成し、前線から出撃させる"""
    for ai_country in ["AI(青)", "AI(緑)"]:
        # 1. 現在のこのAI国家の領地をすべてリストアップ
        ai_nodes = [k for k, v in st.session_state.nodes.items() if v["owner"] == ai_country]
        if not ai_nodes:
            continue  # 領地がなければ出撃できない
            
        # 2. 敵（プレイヤーや中立）と隣接している「前線ノード」を優先的に探す
        frontline_nodes = []
        for node in ai_nodes:
            # 隣接に自分以外の国がいればそこは前線
            if any(st.session_state.nodes[adj]["owner"] != ai_country for adj in st.session_state.nodes[node]["adjacent"]):
                frontline_nodes.append(node)
        
        # もし前線がなければ、自分の領地すべてを出撃候補にする
        spawn_nodes = frontline_nodes if frontline_nodes else ai_nodes
        
        # 出撃の起点となる領地をランダムに決定
        start_node = random.choice(spawn_nodes)
        
        # 3. その起点から「攻め込める隣接ターゲット（他国 or 中立）」を決定
        possible_targets = st.session_state.nodes[start_node]["adjacent"]
        enemy_targets = [adj for adj in possible_targets if st.session_state.nodes[adj]["owner"] != ai_country]
        
        # 攻め込む先（目的地）。周囲がすべて自領なら、通常の隣接ノードへ移動
        target_node = random.choice(enemy_targets) if enemy_targets else random.choice(possible_targets)
        
        # 4. 【新機軸】AI専用プールからランダムに1部隊をコピーしてインスタンス化
        pool_template = random.choice(AI_UNIT_POOL)
        
        # 固有の部隊名を生成（例: AI青軍_ゼウス将軍部隊_T3）
        ai_unit_name = f"{ai_country.replace('(','').replace(')','')}_{pool_template['captain']['name']}部隊_T{st.session_state.turn}"
        
        # グローバル部隊データ（st.session_state.units）に実体化させて目的地に配置！
        st.session_state.units[ai_unit_name] = {
            "owner": ai_country,
            "captain": pool_template["captain"].copy(),
            "soldier_type": pool_template["soldier_type"],
            "count": pool_template["count"],
            "location": target_node, # 目的地へ直接出現（出撃）
            "moved": True            # 出現ターンは行動済み
        }
        
        # 5. 目的地に誰も部隊がいない場合、領地の支配権を書き換える
        # （もしプレイヤー部隊がいたら、プレイヤーの侵攻時に戦闘になります）
        is_occupied = any(ui["location"] == target_node and ui["count"] > 0 for ui in st.session_state.units.values() if ui["owner"] != ai_country)
        
        if st.session_state.nodes[target_node]["owner"] != ai_country:
            if not is_occupied:
                st.session_state.nodes[target_node]["owner"] = ai_country
                add_log(f"⚔️ 凶報: {ai_country}がプールから「{pool_template['captain']['name']}」を召喚！ {target_node}へ出撃し占領しました！")
            else:
                add_log(f"⚠️ 警告: {ai_country}の「{pool_template['captain']['name']}」が 我軍の潜む {target_node} へ向けて出撃！一触即発です！")
def generate_improved_node_label(node_id, info):
    owner = info["owner"]
    owner_icon = "👤" if owner == "プレイヤー(赤)" else "🤖" if owner.startswith("AI") else "🏳️"
    staying_units = [u_name for u_name, u_info in st.session_state.units.items() if u_info["location"] == node_id and u_info["count"] > 0]
    
    unit_text = ""
    if staying_units:
        unit_details = [f"[{st.session_state.units[uname]['captain']['name']}]" for uname in staying_units]
        unit_text = "\n" + "\n".join(unit_details)
    else:
        unit_text = "\n(部隊なし)"
    return f"{node_id}\n{owner_icon}\n{unit_text}"

def generate_hover_title(node_id, info):
    staying_units = [u_name for u_name, u_info in st.session_state.units.items() if u_info["location"] == node_id and u_info["count"] > 0]
    unit_logs = "".join([f"・{uname} ({u['soldier_type']} × {u['count']})\n" for uname, u in [(n, st.session_state.units[n]) for n in staying_units]])
    return f"【{node_id}】\n支配国家: {info['owner']}\n経済力: {info['economy']} G\n--- 駐留部隊 ---\n{unit_logs if unit_logs else 'なし'}"

def draw_map_improved():
    net = Network(height="450px", width="100%", bgcolor="#222222", font_color="white")
    for node_id, info in st.session_state.nodes.items():
        color = COLORS[info["owner"]]
        label = generate_improved_node_label(node_id, info)
        title = generate_hover_title(node_id, info)
        
        staying_units = [u for u in st.session_state.units.values() if u["location"] == node_id]
        total_troops = sum(u["count"] for u in staying_units)
        size = 25 + min(20, total_troops * 2)
        
        is_frontline = any(st.session_state.nodes[adj]["owner"] != info["owner"] for adj in info["adjacent"])
        border_width, border_color = (5, "#ffff00") if is_frontline and info["owner"] == "プレイヤー(赤)" else (1, color)
        
        net.add_node(node_id, label=label, size=size, title=title, shape="circle", 
                     borderWidth=border_width, color=dict(border=border_color, background=color),
                     font=dict(size=13, color="white", strokeWidth=2, strokeColor="#000000"))
        
    for node_id, info in st.session_state.nodes.items():
        for adj in info["adjacent"]:
            if node_id < adj: net.add_edge(node_id, adj, color="#555555", width=2)
                
    net.toggle_physics(False) 
    net.set_options('{"interaction": {"hover": true}, "nodes": {"font": {"face": "monospace"}}}')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "map.html")
        net.save_graph(path)
        with open(path, 'r', encoding='utf-8') as f: html_data = f.read()
    components.html(html_data, height=460)


# --- 4. メインレイアウト制御 ---
# 💡 戦場フェーズの場合は上部マップを隠して戦闘画面に集中させる
if st.session_state.phase != "戦場フェーズ":
    st.title("🌐 ノード奪還戦：🗺️ 40ノード大戦国")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"ターン: {st.session_state.turn} | 現在のフェーズ: 【{st.session_state.phase}】")
        draw_map_improved()
    with col2:
        st.subheader("📊 プレイヤー情報")
        p_gold = st.session_state.country_data["プレイヤー(赤)"]["gold"]
        p_caps = [c["name"] for c in st.session_state.country_data["プレイヤー(赤)"]["captains"]]
        busy_caps = [u["captain"]["name"] for u in st.session_state.units.values() if u["owner"] == "プレイヤー(赤)" and u["count"] > 0]
        free_caps = [c for c in p_caps if c not in busy_caps]
        
        st.metric("所持金 (G)", f"{p_gold} G")
        st.write(f"**未配属の隊長:** {', '.join(free_caps) if free_caps else 'なし'}")
        st.subheader("📜 戦況履歴")
        st.caption("\n".join(st.session_state.log[:6]))
    st.divider()


# --- 5. フェーズごとのUI処理 ---

if st.session_state.phase == "資金確保":
    st.info("【資金確保フェーズ】領地の経済力に応じて資金を獲得します。")
    if st.button("💰 資金を回収して内政へ"):
        for country in st.session_state.country_data:
            earned = sum(n["economy"] for n in st.session_state.nodes.values() if n["owner"] == country)
            st.session_state.country_data[country]["gold"] += earned
        for u_name, u_info in st.session_state.units.items():
            if u_info["owner"] == "プレイヤー(赤)": st.session_state.units[u_name]["moved"] = False
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
                st.session_state.phase = "部隊確保"
                st.session_state.current_candidate = random.choice(CAPTAIN_POOL)
                st.rerun()
        if col_skip.button("内政をスキップ"):
            st.session_state.phase = "部隊確保"
            st.session_state.current_candidate = random.choice(CAPTAIN_POOL)
            st.rerun()

elif st.session_state.phase == "部隊確保":
    cand = st.session_state.current_candidate
    st.info(f"【部隊確保フェーズ】仕官希望者: {cand['name']} (攻撃:{cand['atk']}/防御:{cand['dfn']})")
    try:
        st.image(cand["image"], caption=cand["name"], width=320)
    except:
        # 万が一画像ファイルがない場合のダミー枠
        st.warning(f"📷 画像なし\n({cand['name']})")
    col_hire, col_pass = st.columns(2)
    if col_hire.button("🤝 雇用する (60G)"):
        if st.session_state.country_data["プレイヤー(赤)"]["gold"] >= 60:
            st.session_state.country_data["プレイヤー(赤)"]["gold"] -= 60
            st.session_state.country_data["プレイヤー(赤)"]["captains"].append(cand)
            st.session_state.phase = "部隊配置"
            st.rerun()
    if col_pass.button("見送る"):
        st.session_state.phase = "部隊配置"
        st.rerun()

elif st.session_state.phase == "部隊配置":
    st.info("【部隊配置フェーズ】隊長に兵種を配属し部隊を結成します。")
    if not free_caps:
        if st.button("侵攻フェーズへ進む"): st.session_state.phase = "侵攻"; st.rerun()
    else:
        selected_cap_name = st.selectbox("隊長を選択:", free_caps)
        selected_cap_data = next(c for c in st.session_state.country_data["プレイヤー(赤)"]["captains"] if c["name"] == selected_cap_name)
        selected_soldier = st.selectbox("兵種を選択:", list(SOLDIER_TYPES.keys()))
        
        unit_cost = SOLDIER_TYPES[selected_soldier]["cost"]
        max_buy = st.session_state.country_data["プレイヤー(赤)"]["gold"] // unit_cost
        
        if max_buy == 0: st.error("資金不足でこの兵種は雇用できません")
        else:
            troop_count = st.slider("編成する兵数:", min_value=1, max_value=max_buy, value=1)
            player_nodes = [k for k, v in st.session_state.nodes.items() if v["owner"] == "プレイヤー(赤)"]
            deploy_node = st.selectbox("配置領地:", player_nodes)
            
            if st.button(f"🪖 {selected_cap_name}部隊を結成 ({troop_count * unit_cost}G)"):
                st.session_state.country_data["プレイヤー(赤)"]["gold"] -= troop_count * unit_cost
                st.session_state.units[f"{selected_cap_name}部隊"] = {
                    "owner": "プレイヤー(赤)", "captain": selected_cap_data,
                    "soldier_type": selected_soldier, "count": troop_count, "location": deploy_node, "moved": False
                }
                st.rerun()
        if st.button("配置を終了して侵攻へ"): st.session_state.phase = "侵攻"; st.rerun()


# --- 侵攻フェーズ ＆ 接敵ジャッジ ---
elif st.session_state.phase == "侵攻":
    st.info("【侵攻フェーズ】部隊を移動・侵攻させます。")
    player_units = {k: v for k, v in st.session_state.units.items() if v["owner"] == "プレイヤー(赤)" and not v.get("moved", False) and v["count"] > 0}
    
    if not player_units:
        if st.button("🏁 ターン終了（AI行動へ）"):
            run_ai_turn()
            st.session_state.phase = "資金確保"
            st.session_state.turn += 1
            st.rerun()
    else:
        selected_unit_name = st.selectbox("動かす部隊:", list(player_units.keys()))
        unit_info = player_units[selected_unit_name]
        current_loc = unit_info["location"]
        
        possible_destinations = st.session_state.nodes[current_loc]["adjacent"]
        target_loc = st.selectbox("進軍先を選択:", possible_destinations)
        
        # 💡 移動先に敵部隊（青や緑）がいるかチェック
        enemy_units_at_dest = [k for k, v in st.session_state.units.items() if v["location"] == target_loc and v["owner"] != "プレイヤー(赤)" and v["count"] > 0]
        
        if enemy_units_at_dest:
            st.warning(f"⚠️ {target_loc} には敵【{enemy_units_at_dest[0]}】がいます！進軍すると戦闘が始まります。")
        
        if st.button("🚀 部隊を進軍させる"):
            # 移動処理と行動済みロック
            st.session_state.units[selected_unit_name]["location"] = target_loc
            st.session_state.units[selected_unit_name]["moved"] = True
            
            if enemy_units_at_dest:
                # 💡 敵がいるなら「戦場フェーズ」へ移行。対戦データをセット
                st.session_state.active_battle = {
                    "player_unit_name": selected_unit_name,
                    "enemy_unit_name": enemy_units_at_dest[0],
                    "target_node": target_loc
                }
                st.session_state.phase = "戦場フェーズ"
                st.rerun()
            else:
                # 中立・無人地なら即時塗り替え
                st.session_state.nodes[target_loc]["owner"] = "プレイヤー(赤)"
                add_log(f"【占領】{selected_unit_name}が{target_loc}を確保しました。")
                st.rerun()


# --- ⚔️ 6. 新設：戦場フェーズ（Canvasシミュレーション） ---
elif st.session_state.phase == "戦場フェーズ":
    b_info = st.session_state.active_battle
    p_unit = st.session_state.units[b_info["player_unit_name"]]
    e_unit = st.session_state.units[b_info["enemy_unit_name"]]
    
    st.title("⚔️ リアルタイム交戦スクリーパ（戦場フェーズ）")
    st.subheader(f"舞台: {b_info['target_node']}")
    
    # 計算用のステータス抽出
    p_soldier = p_unit["soldier_type"]
    e_soldier = e_unit["soldier_type"]
    
    # 初期HP＝兵数×10 ＋ 隊長補正
    p_max_hp = p_unit["count"] * 10 + p_unit["captain"]["dfn"]
    e_max_hp = e_unit["count"] * 10 + e_unit["captain"]["dfn"]
    
    # 攻撃力・射程のマスター適用
    p_atk = SOLDIER_TYPES[p_soldier]["atk"] + p_unit["captain"]["atk"]
    e_atk = SOLDIER_TYPES[e_soldier]["atk"] + e_unit["captain"]["atk"]
    
    p_range = SOLDIER_TYPES[p_soldier]["range"]
    e_range = SOLDIER_TYPES[e_soldier]["range"]
    
    p_color = SOLDIER_TYPES[p_soldier]["color"]
    e_color = SOLDIER_TYPES[e_soldier]["color"]

    # 左右のステータス表示（画像つき）
    col_p, col_vs, col_e = st.columns([2, 1, 2])
    
    with col_p:
        st.markdown(f"### 🔴 我軍: {b_info['player_unit_name']}")
        
        # 💡 プレイヤー将軍の画像を表示
        if "image" in p_unit["captain"]:
            try:
                st.image(p_unit["captain"]["image"], width=320)
            except:
                st.text("👤 [No Image]")
                
        st.markdown(f"**隊長:** {p_unit['captain']['name']}")
        st.write(f"兵種: **{p_soldier}** (x{p_unit['count']})")
        st.write(f"基礎攻撃力: {p_atk} / 弾丸射程: **{p_range}px**")
        
    with col_vs:
        st.markdown("<h2 style='text-align:center; color:yellow; margin-top:50px;'>VS</h2>", unsafe_allow_html=True)
        
    with col_e:
        st.markdown(f"### 🔵 敵軍: {b_info['enemy_unit_name']} ({e_unit['owner']})")
        
        # 💡 AI将軍の画像を表示
        if "image" in e_unit["captain"]:
            try:
                st.image(e_unit["captain"]["image"], width=320)
            except:
                st.text("👤 [No Image]")
                
        st.markdown(f"**隊長:** {e_unit['captain']['name']}")
        st.write(f"兵種: **{e_soldier}** (x{e_unit['count']})")
        st.write(f"基礎攻撃力: {e_atk} / 弾丸射程: **{e_range}px**")

    # --- HTML5 Canvas + JavaScript 弾幕前進エンジン ---
    battle_canvas_html = f"""
    <div style="text-align: center; background: #222; padding: 15px; border-radius: 8px;">
        <canvas id="battleCanvas" width="900" height="350" style="background:#111111; border:3px solid #555; max-width:100%;"></canvas>
        <h3 id="statusText" style="color: #fff; font-family: sans-serif; margin-top: 10px;">戦闘中... 🔥</h3>
    </div>
    
    <script>
        const canvas = document.getElementById('battleCanvas');
        const ctx = canvas.getContext('2d');
        
        let p_hp = {p_max_hp};
        let e_hp = {e_max_hp};
        const p_max = {p_max_hp};
        const e_max = {e_max_hp};
        
        let p_x = 80, p_y = 175;
        let e_x = 820, e_y = 175;
        
        const p_speed = 1.5;
        const e_speed = 1.5;
        
        let bullets = [];
        let battleOver = false;

        function drawHPBars() {{
            ctx.fillStyle = '#555'; ctx.fillRect(40, 20, 250, 15);
            ctx.fillStyle = '#ff4b4b'; ctx.fillRect(40, 20, (p_hp / p_max) * 250, 15);
            ctx.fillStyle = '#fff'; ctx.font = '12px sans-serif'; ctx.fillText('プレイヤーHP: ' + Math.max(0, Math.floor(p_hp)), 45, 32);
            
            ctx.fillStyle = '#555'; ctx.fillRect(610, 20, 250, 15);
            ctx.fillStyle = '#1c83e1'; ctx.fillRect(610, 20, (e_hp / e_max) * 250, 15);
            ctx.fillStyle = '#fff'; ctx.fillText('敵軍HP: ' + Math.max(0, Math.floor(e_hp)), 615, 32);
        }}

        function animate() {{
            if (battleOver) return;
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawHPBars();
            
            let current_distance = Math.abs(e_x - p_x);
            if (current_distance > {p_range} && p_x < e_x - 50) {{ p_x += p_speed; }}
            if (current_distance > {e_range} && e_x > p_x + 50) {{ e_x -= e_speed; }}
            
            ctx.fillStyle = '{p_color}';
            ctx.beginPath(); ctx.arc(p_x, p_y, 25, 0, Math.PI*2); ctx.fill();
            ctx.fillStyle = '#fff'; ctx.font = '14px sans-serif'; ctx.fillText('🔴', p_x-8, p_y+4);
            
            ctx.fillStyle = '{e_color}';
            ctx.beginPath(); ctx.arc(e_x, e_y, 25, 0, Math.PI*2); ctx.fill();
            ctx.fillStyle = '#fff'; ctx.font = '14px sans-serif'; ctx.fillText('🔵', e_x-8, e_y+4);
            
            if(Math.random() < 0.08 && p_hp > 0) {{
                bullets.push({{x: p_x + 25, y: p_y + (Math.random()*20-10), vx: 7, max_x: p_x + {p_range}, side: 'p', color: '{p_color}'}});
            }}
            if(Math.random() < 0.08 && e_hp > 0) {{
                bullets.push({{x: e_x - 25, y: e_y + (Math.random()*20-10), vx: -7, max_x: e_x - {e_range}, side: 'e', color: '{e_color}'}});
            }}
            
            for(let i = bullets.length - 1; i >= 0; i--) {{
                let b = bullets[i];
                b.x += b.vx;
                ctx.fillStyle = b.color;
                ctx.beginPath(); ctx.arc(b.x, b.y, 5, 0, Math.PI*2); ctx.fill();
                
                if((b.vx > 0 && b.x > b.max_x) || (b.vx < 0 && b.x < b.max_x)) {{
                    bullets.splice(i, 1); continue;
                }}
                
                if(b.side === 'p' && Math.abs(b.x - e_x) <= 25 && Math.abs(b.y - e_y) <= 25) {{
                    e_hp -= {p_atk} * (0.8 + Math.random()*0.4);
                    bullets.splice(i, 1);
                    if(e_hp <= 0) {{ endBattle('WIN'); break; }}
                    continue;
                }}
                if(b.side === 'e' && Math.abs(b.x - p_x) <= 25 && Math.abs(b.y - p_y) <= 25) {{
                    p_hp -= {e_atk} * (0.8 + Math.random()*0.4);
                    bullets.splice(i, 1);
                    if(p_hp <= 0) {{ endBattle('LOSE'); break; }}
                    continue;
                }}
            }}
            requestAnimationFrame(animate);
        }}

        function endBattle(result) {{
            battleOver = true;
            document.getElementById('statusText').innerText = result === 'WIN' ? '🎉 WIN！敵部隊の撃破を確認しました！下のボタンを押してリザルトを確定してください。' : '💀 LOSE... 我軍の壊滅を確認しました。下のボタンを押して戻ってください。';
        }}

        animate();
    </script>
    """
    
    # Canvasを画面にレンダリング
    components.html(battle_canvas_html, height=430)
    
    # --- Streamlit側で確実にキャッチする結果確定UI ---
    st.markdown("### 📝 戦闘結果の確定")
    st.info("上のミニ画面で勝敗（WIN / LOSE）が決まったら、該当するボタンを押して戦果を記録してください。")
    
    col_w, col_l = st.columns(2)
    
    with col_w:
        if st.button("🏆 我軍の「勝利(WIN)」を確定して領地を占領", use_container_width=True):
            add_log(f"⚔️【大勝利】{b_info['player_unit_name']}が{b_info['target_node']}で{b_info['enemy_unit_name']}を撃破！")
            # 敵部隊の消滅と領地の占領
            if b_info["enemy_unit_name"] in st.session_state.units:
                st.session_state.units[b_info["enemy_unit_name"]]["count"] = 0
            st.session_state.nodes[b_info["target_node"]]["owner"] = "プレイヤー(赤)"
            
            # 状態をリセットして侵攻フェーズへ
            st.session_state.phase = "侵攻"
            st.rerun()
            
    with col_l:
        if st.button("🏳️ 我軍の「敗北(LOSE)」を確定して部隊解散", use_container_width=True):
            add_log(f"⚔️【惨敗】{b_info['player_unit_name']}は{b_info['target_node']}の戦闘で壊滅しました...")
            # 自軍部隊の消滅
            if b_info["player_unit_name"] in st.session_state.units:
                st.session_state.units[b_info["player_unit_name"]]["count"] = 0
                
            # 状態をリセットして侵攻フェーズへ
            st.session_state.phase = "侵攻"
            st.rerun()