import streamlit as st
import random
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile
import os
# 画面全体のレイアウトを広く使う
st.set_page_config(layout="wide")

# --- 1. 定数と初期データ定義 ---
COUNTRIES = ["プレイヤー(赤)", "AI(青)", "AI(緑)", "中立"]
COLORS = {"プレイヤー(赤)": "#ff4b4b", "AI(青)": "#1c83e1", "AI(緑)": "#00f060", "中立": "#aaaaaa"}

CAPTAIN_POOL = [
    {"name": "レオニダス", "atk": 15, "dfn": 10, "mot": 5},
    {"name": "ジャンヌ", "atk": 10, "dfn": 15, "mot": 8},
    {"name": "オダ・ノブナガ", "atk": 18, "dfn": 8, "mot": 4},
    {"name": "アーサー", "atk": 12, "dfn": 12, "mot": 6},
    {"name": "アレクサンダー", "atk": 14, "dfn": 11, "mot": 7},
]

# --- 2. セッション状態の初期化（初回のみ実行） ---
# キー `map_generated` を使って、2回目以降の再実行でマップが再生成されるのを完全に防ぎます
if "map_generated" not in st.session_state:
    st.session_state.map_generated = True
    st.session_state.phase = "資金確保"
    st.session_state.turn = 1
    
    st.session_state.country_data = {
        "プレイヤー(赤)": {"gold": 100, "captains": []},
        "AI(青)": {"gold": 100, "captains": [{"name": "AI将軍A", "atk": 10, "dfn": 10, "mot": 5}]},
        "AI(緑)": {"gold": 100, "captains": [{"name": "AI将軍B", "atk": 10, "dfn": 10, "mot": 5}]},
    }
    
    num_nodes = 40
    nodes = {}
    
    # 初期領地配置
    for i in range(num_nodes):
        node_id = f"領地_{i+1}"
        if i == 0: owner = "プレイヤー(赤)"
        elif i == 1: owner = "AI(青)"
        elif i == 2: owner = "AI(緑)"
        else: owner = "中立"
        
        nodes[node_id] = {
            "owner": owner,
            "economy": random.randint(10, 50),
            "troops": random.randint(10, 20) if owner != "中立" else random.randint(2, 6),
            "adjacent": set()
        }
    
    # 固定のネットワーク構造を生成
    node_keys = list(nodes.keys())
    for i in range(num_nodes - 1):
        nodes[node_keys[i]]["adjacent"].add(node_keys[i+1])
        nodes[node_keys[i+1]]["adjacent"].add(node_keys[i])
    
    # 複雑化のためのランダムエッジ（初回のみ固定で生成される）
    random.seed(42) # 形状を完全に固定したい場合はシード値を設定
    for _ in range(50):
        n1 = random.choice(node_keys)
        n2 = random.choice(node_keys)
        if n1 != n2:
            nodes[n1]["adjacent"].add(n2)
            nodes[n2]["adjacent"].add(n1)
            
    for n in nodes:
        nodes[n]["adjacent"] = list(nodes[n]["adjacent"])
        
    st.session_state.nodes = nodes
    st.session_state.log = ["世界が生成されました。天下統一を目指しましょう！"]
    st.session_state.current_candidate = random.choice(CAPTAIN_POOL)

# --- 3. 共通関数 ---
def add_log(text):
    st.session_state.log.insert(0, f"【T{st.session_state.turn}】{text}")

def draw_map():
    net = Network(height="450px", width="100%", bgcolor="#222222", font_color="white")
    for node_id, info in st.session_state.nodes.items():
        color = COLORS[info["owner"]]
        label = f"{node_id}\n(兵:{info['troops']}/経:{info['economy']})"
        net.add_node(node_id, label=label, color=color, size=22)
        
    for node_id, info in st.session_state.nodes.items():
        for adj in info["adjacent"]:
            if node_id < adj:
                net.add_edge(node_id, adj, color="#555555")
                
    net.toggle_physics(False)
    
    # 💡 修正ポイント: 一時フォルダ内にHTMLを出力する
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "map.html")
        net.save_graph(path)
        with open(path, 'r', encoding='utf-8') as f:
            html_data = f.read()
            
    components.html(html_data, height=460)
# --- AIの侵攻処理関数 ---
def run_ai_turn():
    """青国と緑国がそれぞれ隣接する他国・中立の領地にランダムに攻め込む"""
    for ai_country in ["AI(青)", "AI(緑)"]:
        # AIが持っていて、かつ兵力が2以上の領地（出撃元候補）
        ai_nodes = [k for k, v in st.session_state.nodes.items() if v["owner"] == ai_country and v["troops"] > 2]
        
        if not ai_nodes:
            continue
            
        # ランダムに1つの領地から出撃
        src_node = random.choice(ai_nodes)
        
        # 隣接する「敵地」または「中立地」をリストアップ
        possible_targets = [adj for adj in st.session_state.nodes[src_node]["adjacent"] if st.session_state.nodes[adj]["owner"] != ai_country]
        
        if not possible_targets:
            continue
            
        tgt_node = random.choice(possible_targets)
        
        # 半分の兵力を出撃させる
        atk_troops = st.session_state.nodes[src_node]["troops"] // 2
        if atk_troops < 1:
            continue
            
        # 戦闘計算（簡易版）
        ai_atk = atk_troops + random.randint(1, 10)
        def_info = st.session_state.nodes[tgt_node]
        def_val = def_info["troops"] + random.randint(1, 10)
        
        if ai_atk > def_val:
            # AIの勝利
            survivors = max(1, atk_troops - (def_val // 2))
            st.session_state.nodes[src_node]["troops"] -= atk_troops
            old_owner = st.session_state.nodes[tgt_node]["owner"]
            st.session_state.nodes[tgt_node]["owner"] = ai_country
            st.session_state.nodes[tgt_node]["troops"] = survivors
            add_log(f"⚔️ 凶報: {ai_country}が {src_node} から {tgt_node}(元:{old_owner}) へ侵攻し、占領しました！")
        else:
            # AIの敗北
            st.session_state.nodes[src_node]["troops"] -= atk_troops
            st.session_state.nodes[tgt_node]["troops"] = max(1, def_info["troops"] - (atk_troops // 2))

# --- 4. 画面表示レイアウト ---
st.title("🌐 ノード奪還戦：🗺️ 40ノード大戦国")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"ターン: {st.session_state.turn} | 現在のフェーズ: 【{st.session_state.phase}】")
    draw_map()

with col2:
    st.subheader("📊 プレイヤー情報")
    p_gold = st.session_state.country_data["プレイヤー(赤)"]["gold"]
    p_caps = [c["name"] for c in st.session_state.country_data["プレイヤー(赤)"]["captains"]]
    st.metric("所持金 (G)", f"{p_gold} G")
    st.write(f"**配下の隊長:** {', '.join(p_caps) if p_caps else 'なし'}")
    
    st.subheader("📜 戦況履歴")
    st.caption("\n".join(st.session_state.log[:10]))

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
        if col_inv.button("💸 50G投資する (経済力+20)"):
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
    st.info("【部隊配置フェーズ】所持金を使って兵力を購入・配備します（1兵力 = 2G）。")
    player_nodes = [k for k, v in st.session_state.nodes.items() if v["owner"] == "プレイヤー(赤)"]
    
    if player_nodes:
        target_node = st.selectbox("配備先の領地:", player_nodes)
        max_affordable = st.session_state.country_data["プレイヤー(赤)"]["gold"] // 2
        amount = st.number_input("配備する兵力数:", min_value=0, max_value=max_affordable, value=0)
        
        if st.button("🪖 兵力を確定して侵攻フェーズへ"):
            if amount > 0:
                st.session_state.country_data["プレイヤー(赤)"]["gold"] -= (amount * 2)
                st.session_state.nodes[target_node]["troops"] += amount
                add_log(f"{target_node} に兵力を {amount} 補充しました。")
            st.session_state.phase = "侵攻"
            st.rerun()
    else:
        st.session_state.phase = "侵攻"
        st.rerun()

elif st.session_state.phase == "侵攻":
    st.info("【侵攻フェーズ】自分のターンを終了すると、同時にAI国家（青・緑）も行動を開始します。")
    
    atk_sources = [k for k, v in st.session_state.nodes.items() if v["owner"] == "プレイヤー(赤)" and v["troops"] > 1]
    valid_sources = [src for src in atk_sources if any(st.session_state.nodes[adj]["owner"] != "プレイヤー(赤)" for adj in st.session_state.nodes[src]["adjacent"])]
    
    col_atk, col_end = st.columns(2)
    
    with col_atk:
        if valid_sources:
            src_node = st.selectbox("出撃元:", valid_sources)
            possible_targets = [adj for adj in st.session_state.nodes[src_node]["adjacent"] if st.session_state.nodes[adj]["owner"] != "プレイヤー(赤)"]
            tgt_node = st.selectbox("攻撃先:", possible_targets)
            
            max_atk_troops = st.session_state.nodes[src_node]["troops"] - 1
            
            # 💡 修正ポイント: 出撃可能最大数が1の場合はスライダーを出さずに1に固定
            if max_atk_troops == 1:
                st.write("⚔️ 出撃兵力: **1** (領地に1名残すため選択の余地がありません)")
                atk_troops = 1
            else:
                atk_troops = st.slider("出撃兵力", min_value=1, max_value=max_atk_troops, value=max_atk_troops)
            
            if st.button("⚔️ 侵攻開始！"):
                # プレイヤー戦闘
                p_caps = st.session_state.country_data["プレイヤー(赤)"]["captains"]
                cap_atk_bonus = sum(c["atk"] + c["mot"] for c in p_caps) // len(p_caps) if p_caps else 0
                total_atk = atk_troops + cap_atk_bonus + random.randint(1, 10)
                
                def_info = st.session_state.nodes[tgt_node]
                total_dfn = def_info["troops"] + random.randint(1, 10)
                
                if total_atk > total_dfn:
                    survivors = max(1, atk_troops - (total_dfn // 2))
                    st.session_state.nodes[src_node]["troops"] -= atk_troops
                    st.session_state.nodes[tgt_node]["owner"] = "プレイヤー(赤)"
                    st.session_state.nodes[tgt_node]["troops"] = survivors
                    add_log(f"🎉 勝利！ {tgt_node}を占領しました。")
                else:
                    st.session_state.nodes[src_node]["troops"] -= atk_troops
                    st.session_state.nodes[tgt_node]["troops"] = max(1, def_info["troops"] - (atk_troops // 2))
                    add_log(f"😢 敗北... {tgt_node} の攻略に失敗しました。")
                
                # プレイヤー行動後にAIが行動
                run_ai_turn()
                st.session_state.phase = "資金確保"
                st.session_state.turn += 1
                st.rerun()
        else:
            st.write("攻め込める隣接領地がありません。")
            
    with col_end:
        if st.button("🏁 侵攻せずにターン終了（AIのみ行動）"):
            run_ai_turn()
            st.session_state.phase = "資金確保"
            st.session_state.turn += 1
            st.rerun()