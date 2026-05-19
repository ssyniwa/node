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
# --- プレイヤー用将軍プール ---
CAPTAIN_POOL = [
    {"name": "レオニダス", "atk": 15, "dfn": 10, "mot": 5, "image": "assets/reonidas.png", "skill_id": "spartan_wall", "skill_name": "スパルタの不撓不屈", "skill_desc": "ピンチ時に絶対防御"},
    {"name": "ジャンヌ", "atk": 10, "dfn": 15, "mot": 8, "image": "assets/zannu.png", "skill_id": "holy_prayer", "skill_name": "聖女の進軍祈祷", "skill_desc": "部隊移動速度1.5倍"},
    {"name": "ノブナガ", "atk": 18, "dfn": 8, "mot": 4, "image": "assets/nobunaga.png", "skill_id": "three_line_fire", "skill_name": "三段撃ちの烈火", "skill_desc": "弾丸の発射確率が2倍"},
    {"name": "アーサー", "atk": 12, "dfn": 12, "mot": 6, "image": "assets/arther.png", "skill_id": "avalon_bless", "skill_name": "円卓の加護", "skill_desc": "戦闘終了後にHP回復"},
    {"name": "アレクサンダー", "atk": 14, "dfn": 11, "mot": 7, "image": "assets/arexander.png", "skill_id": "phalanx_push", "skill_name": "東方遠征の覇道", "skill_desc": "常時攻撃力プラス"},
    {"name": "あかね", "atk": 13, "dfn": 14, "mot": 10, "image": "assets/akane.png", "skill_id": "crimson_drive", "skill_name": "紅蓮の情熱", "skill_desc": "弾丸速度アップ"},
    {"name": "しずく", "atk": 16, "dfn": 16, "mot": 12, "image": "assets/sizuku.png", "skill_id": "clear_mind", "skill_name": "明鏡止水の戦術", "skill_desc": "敵の攻撃力ダウン"},
    {"name": "みつば", "atk": 12, "dfn": 18, "mot": 13, "image": "assets/mituba.png", "skill_id": "clover_luck", "skill_name": "三つ葉の幸運", "skill_desc": "資金確保の収入UP"},
    {"name": "あいり", "atk": 17, "dfn": 12, "mot": 5, "image": "assets/airi.png", "skill_id": "gale_strike", "skill_name": "疾風怒濤の連撃", "skill_desc": "確率でクリティカル"},
    {"name": "カイル", "atk": 14, "dfn": 14, "mot": 9, "image": "assets/kyle.png", "skill_id": "iron_discipline", "skill_name": "鉄の規律", "skill_desc": "領地投資の費用割引"},
    {"name": "ケイト", "atk": 19, "dfn": 9, "mot": 4, "image": "assets/kate.png", "skill_id": "lightning_raid", "skill_name": "電撃の強襲作戦", "skill_desc": "開幕に先制弾発射"},
]

# --- AI専用の出撃待ち部隊プール ---
AI_UNIT_POOL = [
    {"captain": {"name": "AIA", "atk": 18, "dfn": 9, "image": "assets/aia.png", "skill_id": "sky_ace", "skill_name": "第1空軍の猛威", "skill_desc": "戦闘機部隊を強化"}, "soldier_type": "戦闘機部隊", "count": 5},
    {"captain": {"name": "AIB", "atk": 14, "dfn": 14, "image": "assets/aib.png", "skill_id": "panzer_charge", "skill_name": "鋼鉄の進撃", "skill_desc": "戦車部隊のHPアップ"}, "soldier_type": "戦車部隊", "count": 7},
    {"captain": {"name": "ゼウス", "atk": 20, "dfn": 15, "image": "assets/zeusu.png", "skill_id": "thunder_bolt", "skill_name": "全能なる神の雷霆", "skill_desc": "ミサイルが3方向へ拡散"}, "soldier_type": "ミサイル部隊", "count": 3},
    {"captain": {"name": "カエサル", "atk": 12, "dfn": 18, "image": "assets/kaesaru.png", "skill_id": "imperator_tactics", "skill_name": "賽は投げられた", "skill_desc": "射程距離が大幅アップ"}, "soldier_type": "戦車部隊", "count": 5},
    {"captain": {"name": "ナポレオン", "atk": 16, "dfn": 10, "image": "assets/naporeon.png", "skill_id": "artillery_god", "skill_name": "皇帝の飽和砲撃", "skill_desc": "砲撃の範囲拡大"}, "soldier_type": "砲撃部隊", "count": 8},
    {"captain": {"name": "ハンニバル", "atk": 15, "dfn": 12, "image": "assets/hannibaru.png", "skill_id": "alps_tactics", "skill_name": "アルプス越えの奇襲", "skill_desc": "前進した位置から開始"}, "soldier_type": "戦闘機部隊", "count": 4},
    {"captain": {"name": "チンギスハーン", "atk": 14, "dfn": 8, "image": "assets/tingishun.png", "skill_id": "nomad_arrow", "skill_name": "蒼き狼の騎射", "skill_desc": "銃撃部隊を超強化"}, "soldier_type": "銃撃部隊", "count": 15},
    {"captain": {"name": "シバ", "atk": 10, "dfn": 10, "image": "assets/siba.png", "skill_id": "queen_wealth", "skill_name": "シバ王国の財力", "skill_desc": "毎ターン領地経済UP"}, "soldier_type": "銃撃部隊", "count": 10},
    {"captain": {"name": "マリー", "atk": 13, "dfn": 14, "image": "assets/mary.png", "skill_id": "royal_splendor", "skill_name": "宮廷の華麗なる威風", "skill_desc": "確率で敵の弾を無効化"}, "soldier_type": "砲撃部隊", "count": 6},
    {"captain": {"name": "クレオパトラ", "atk": 17, "dfn": 11, "image": "assets/kure.png", "skill_id": "alluring_charm", "skill_name": "王妃の誘惑", "skill_desc": "敵の連射力を低下"}, "soldier_type": "戦車部隊", "count": 4},
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

def generate_random_map(num_nodes):
    """指定されたノード数で、孤立点のないネットワークマップを自動生成する"""
    nodes = {}
    
    # 1. 座標の決定（画面の適度な範囲に分散させる）
    # 10個なら広々と、40個なら細かく配置
    for i in range(1, num_nodes + 1):
        name = f"領地{i}"
        # 重なりすぎないように簡易的なランダム配置（マップのサイズに合わせて調整）
        x = random.randint(100, 800)
        y = random.randint(100, 500)
        
        # 最初の3つの領地は、各国（プレイヤー、AI青、AI緑）の首都として固定オーナーにする
        if i == 1:
            owner = "プレイヤー(赤)"
        elif i == 4:
            owner = "AI(青)"
        elif i == 7:
            owner = "AI(緑)"
        else:
            owner = "中立"
            
        nodes[name] = {
            "x": x,
            "y": y,
            "owner": owner,
            "adjacent": [],
            "economy": random.randint(10, 50)  # 💡 ココを追加！各領地に10〜50Gのランダムな経済力を持たせる
        }
    
    # 2. 隣接関係（エッジ）の自動接続（すべての領地がいずれかと繋がるようにする）
    node_names = list(nodes.keys())
    
    # 線の通り道を確保するため、まずは一本道（ツリー）を作って孤立を防ぐ
    for i in range(num_nodes - 1):
        n1 = node_names[i]
        n2 = node_names[i+1]
        nodes[n1]["adjacent"].append(n2)
        nodes[n2]["adjacent"].append(n1)
        
    # さらにランダムに近くのノード同士を結んで、戦略的な抜け道を作る
    for name, data in nodes.items():
        # 現在の接続数が少ない場合、距離が近い順に2つ選んで接続
        if len(data["adjacent"]) < 3:
            # 他のノードを距離順にソート
            others = [n for n in node_names if n != name and n not in data["adjacent"]]
            if others:
                # 1〜2個の追加経路をランダムに接続
                for extra in random.sample(others, min(len(others), random.randint(1, 2))):
                    nodes[name]["adjacent"].append(extra)
                    nodes[extra]["adjacent"].append(name)
                    
    # 重複を排除
    for name in nodes:
        nodes[name]["adjacent"] = list(set(nodes[name]["adjacent"]))
        
    return nodes
        
    
# --- 3. 共通ロジック ---
def add_log(text):
    st.session_state.logs.insert(0, f"【T{st.session_state.turn}】{text}")

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

if "game_started" not in st.session_state:
    st.session_state.game_started = False

# ==============================================================================
# Aパターン：ゲーム開始前の「初期設定（タイトル）画面」
# ==============================================================================
if not st.session_state.game_started:
    # 💡 整合性のポイント：この時点では st.sidebar は使わず、メイン画面中央に設定をスッキリ出す
    st.title("⚔️ 簡易戦略シミュレーションゲーム")
    st.markdown("### 🗺️ 初期設定")
    
    selected_size = st.selectbox("戦場の規模（領地数）を選択してください", [10, 20, 30, 40], index=1)
    
    if st.button("🚀 この規模で世界大戦を開始する", use_container_width=True):
        # --- ここで一斉に初期データをセッションに格納 ---
        st.session_state.nodes = generate_random_map(selected_size)
        st.session_state.turn = 1
        st.session_state.phase = "資金確保" # 💡 最初のフェーズはお好みで（例: 最初に部隊確保させたいならここを「部隊確保」にする）
        st.session_state.logs = ["📢 大戦の火蓋が切って落とされた！"]
        st.session_state.current_candidate = random.choice(CAPTAIN_POOL)
        
        # ゲーム開始フラグをONにして画面を即リフレッシュ！
        st.session_state.game_started = True
        st.rerun()
else:
    # ==============================================================================
    # Bパターン：いつものメインゲーム画面（ゲーム開始後にのみ実行される）
    # ==============================================================================
    if st.session_state.phase != "戦場フェーズ":
        # 💡 整合性のポイント：ゲーム開始後は、これまでのメインレイアウト制御（サイドバー等）を100%そのまま動かす！
        # ==============================================================================
        # 🏆 👑 【新機能】ゲームクリア / ゲームオーバーのリアルタイム判定
        # ==============================================================================
        # 全領地（ノード）のオーナーのリストを取得
        all_owners = [node_info["owner"] for node_info in st.session_state.nodes.values()]
        
        # プレイヤー（赤）が持っている領地の数をカウント
        player_land_count = all_owners.count("プレイヤー(赤)")
        total_lands = len(all_owners)
        
        # 条件A：プレイヤーの領地がゼロになった ➡️ 【ゲームオーバー】
        if player_land_count == 0:
            st.markdown("<h1 style='text-align: center; color: #ff4b4b; font-size: 60px; margin-top: 50px;'>💀 GAME OVER</h1>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; color: #aaa;'>あなたの国は敵国に蹂躙され、滅亡しました…</h3>", unsafe_allow_html=True)
            
            # 滅亡時の悲壮なスタッツ表示
            st.error(f"生存ターン数: {st.session_state.turn} ターン")
            
            st.write("---")
            # ゲームクリア、またはゲームオーバーの画面内にあるボタン処理を以下に差し替え
            if st.button("🔄 もう一度最初からやり直す", use_container_width=True):
                # セッション状態をすべてクリア
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.game_started = False
                st.rerun()
            st.stop() # 💡 これ以降の通常のマップやフェーズ画面を描画させずにここで止める！

        # 条件B：プレイヤーの領地数が全領地数と等しくなった（中立も敵もゼロ） ➡️ 【ゲームクリア】
        elif player_land_count == total_lands:
            st.markdown("<h1 style='text-align: center; color: #ffd700; font-size: 60px; margin-top: 50px;'>👑 VICTORY CLEAR!</h1>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; color: #fff;'>おめでとうございます！あなたは全土を統一し、世界に覇を唱えました！</h3>", unsafe_allow_html=True)
            
            # 統一時の栄誉スタッツ表示
            st.balloons() # 🎉 画面にお祝いの風船を飛ばすStreamlit公式演出！
            st.success(f"👑 統一達成ターン数: {st.session_state.turn} ターン (規模: {total_lands}ノード)")
            
            st.write("---")
            if st.button("🗺️ 新たな覇道へ（別の規模で遊ぶ）", use_container_width=True, type="primary"):
                st.session_state.game_started = False
                st.rerun()
            st.stop() # 💡 これ以降の通常のマップやフェーズ画面を描画させずにここで止める！
        # --- 1. サイドバー領域（ターン数、現在のフェーズ、現在の軍資金などのメタ情報） ---
        with st.sidebar:
            st.header(f"⏳ ターン: {st.session_state.turn}")
            st.subheader(f"現在フェーズ: 【{st.session_state.phase}】")
            st.write("---")
            # ログの表示など、これまでサイドバーに入れていたものをここに記述
            st.markdown("### 📜 戦況ログ")
            for log in reversed(st.session_state.logs[-10:]): # 直近10件
                st.caption(log)

        # --- 2. メインエリア領域（フェーズごとの画面制御） ---
        st.title("🗺️ 盤面マップ・戦況報告")

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
            
        st.divider()


    # --- 5. フェーズごとのUI処理 ---

    if st.session_state.phase == "資金確保":
        st.info("【資金確保フェーズ】領地の経済力に応じて資金を獲得します。")
        if st.button("💰 資金を回収して内政へ"):
            for country in st.session_state.country_data:
                earned = sum(n["economy"] for n in st.session_state.nodes.values() if n["owner"] == country)
                # 💡 みつばのスキル判定：プレイヤー部隊の誰かに「みつば」がいればボーナス
                has_mituba = any(u.get("captain", {}).get("skill_id") == "clover_luck" for u in st.session_state.units.values() if u["owner"] == "プレイヤー(赤)")

                if has_mituba:
                    earned += 20
                    add_log("🍀 スキル発動【三つ葉の幸運】により、今ターンの収入が +20G されました！")
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
            # 💡 カイルのスキル判定：プレイヤー部隊に「カイル」がいれば費用20%オフ
            has_kyle = any(u.get("captain", {}).get("skill_id") == "iron_discipline" for u in st.session_state.units.values() if u["owner"] == "プレイヤー(赤)")

            base_cost = 50  # 通常の投資コスト
            invest_cost = int(base_cost * 0.8) if has_kyle else base_cost

            if col_inv.button(f"領地を開発する (消費: {invest_cost}G)"):
                if st.session_state.gold >= invest_cost:
                    st.session_state.gold -= invest_cost
                    # (ここに既存の経済UPロジック)
                    if has_kyle:
                        add_log("⚙️ スキル発動【鉄の規律】により、投資費用が20%割引されました。")
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
                # 選択した領地にいる敵部隊をすべて抽出
                target_node = target_loc
                enemy_units_in_node = [
                    {"id": uid, "data": u} for uid, u in st.session_state.units.items()
                    if u["location"] == target_node and u["owner"] != "プレイヤー(赤)"
                ]
                
                if enemy_units_in_node:
                    # 💡 【複数部隊対応】配列の先頭（1番目の部隊）だけを今回の戦闘相手にする
                    active_enemy = enemy_units_in_node[0]
                    enemy_uid = active_enemy["id"]
                    e_unit = active_enemy["data"]
                    
                    # プレイヤーの選択部隊
                    p_uid = st.session_state.selected_unit_name
                    p_unit = st.session_state.units[p_uid]
                    
                    # 戦闘情報をセッションに保存
                    st.session_state.battle_info = {
                        "player_uid": p_uid,
                        "enemy_uid": enemy_uid, # 1部隊のみロック
                        "player_unit_name": f"{p_unit['captain']['name']}隊",
                        "enemy_unit_name": f"{e_unit['captain']['name']}隊",
                        "target_node": target_node
                    }
                    
                    # 戦場フェーズへ移行
                    st.session_state.phase = "戦場フェーズ"
                    add_log(f"⚔️ {target_node} の {e_unit['captain']['name']}隊 に向かって進軍しました！")
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

       # 左右のステータス表示（画像＆スキル付き）
        col_p, col_vs, col_e = st.columns([2, 1, 2])
        
        with col_p:
            st.markdown(f"### 🔴 我軍: {b_info['player_unit_name']}")
            if "image" in p_unit["captain"]:
                try: st.image(p_unit["captain"]["image"], width=120)
                except: st.text("👤 [No Image]")
                    
            st.markdown(f"**隊長:** {p_unit['captain']['name']}")
            
            # 💡 【新設】プレイヤースキルバッジの表示
            p_skill_id = p_unit["captain"].get("skill_id", "none")
            p_skill_name = p_unit["captain"].get("skill_name", "なし")
            p_skill_desc = p_unit["captain"].get("skill_desc", "")
            st.markdown(f"⚡ **固有スキル: {p_skill_name}**")
            st.caption(f"効果: {p_skill_desc}")
            
            st.write(f"兵種: **{p_soldier}** (x{p_unit['count']})")
            st.write(f"基礎攻撃力: {p_atk} / 弾丸射程: **{p_range}px**")
            
        with col_vs:
            st.markdown("<h2 style='text-align:center; color:yellow; margin-top:60px;'>VS</h2>", unsafe_allow_html=True)
            
        with col_e:
            st.markdown(f"### 🔵 敵軍: {b_info['enemy_unit_name']} ({e_unit['owner']})")
            if "image" in e_unit["captain"]:
                try: st.image(e_unit["captain"]["image"], width=120)
                except: st.text("👤 [No Image]")
                    
            st.markdown(f"**隊長:** {e_unit['captain']['name']}")
            
            # 💡 【新設】AIスキルバッジの表示
            e_skill_id = e_unit["captain"].get("skill_id", "none")
            e_skill_name = e_unit["captain"].get("skill_name", "なし")
            e_skill_desc = e_unit["captain"].get("skill_desc", "")
            st.markdown(f"⚡ **固有スキル: {e_skill_name}**")
            st.caption(f"効果: {e_skill_desc}")
            
            st.write(f"兵種: **{e_soldier}** (x{e_unit['count']})")
            st.write(f"基礎攻撃力: {e_atk} / 弾丸射程: **{e_range}px**")

        # --- HTML5 Canvas + JavaScript 弾幕前進エンジン（スキル連動版） ---
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

            // 💡 【スキル反映：AIB】敵がAIBなら最大HP+50
            const p_max = {p_max_hp};
            let e_max = {e_max_hp};
            if ("{e_skill_id}" === "panzer_charge") {{ e_max += 50; e_hp += 50; }}

            let p_x = 80, p_y = 175;
            let e_x = 820, e_y = 175;

            // 💡 【スキル反映：ハンニバル】敵がハンニバルなら少し前進した位置から開始
            if ("{e_skill_id}" === "alps_tactics") {{ e_x = 700; }}

            // 💡 【スキル反映：ジャンヌ】
            let p_speed = 1.5;
            if ("{p_skill_id}" === "holy_prayer") {{ p_speed = 2.25; }}
            let e_speed = 1.5;

            // 💡 【スキル反映：カエサル】
            let p_range_val = {p_range};
            let e_range_val = {e_range};
            if ("{e_skill_id}" === "imperator_tactics") {{ e_range_val += 150; }}

            // 💡 【スキル反映：ノブナガ / クレオパトラ】
            let p_fire_rate = 0.08;
            if ("{p_skill_id}" === "three_line_fire") {{ p_fire_rate = 0.16; }}
            if ("{e_skill_id}" === "alluring_charm") {{ p_fire_rate = 0.04; }} // プレイヤーの連射半減
            let e_fire_rate = 0.08;

            // 💡 【スキル反映：しずく】敵の基礎攻撃力を30%ダウン
            let p_atk_val = {p_atk};
            let e_atk_val = {e_atk};
            if ("{p_skill_id}" === "clear_mind") {{ e_atk_val *= 0.7; }}
            // 💡 【スキル反映：アレクサンダー / AIA】
            if ("{p_skill_id}" === "phalanx_push") {{ p_atk_val += 2; }}
            if ("{e_skill_id}" === "sky_ace" && "{e_soldier}" === "戦闘機部隊") {{ e_atk_val *= 1.3; }}

            // 無敵フラグ（レオニダス用）
            let p_is_immune = false;
            let p_immune_used = false;

            let bullets = [];
            let battleOver = false;

            function drawHPBars() {{
                ctx.fillStyle = '#555'; ctx.fillRect(40, 20, 250, 15);
                ctx.fillStyle = '#ff4b4b'; ctx.fillRect(40, 20, (p_hp / p_max) * 250, 15);
                ctx.fillStyle = '#fff'; ctx.font = '12px sans-serif'; ctx.fillText('プレイヤーHP: ' + Math.max(0, Math.floor(p_hp)), 45, 32);
                if(p_is_immune) {{ ctx.fillStyle = 'yellow'; ctx.fillText('🛡️ 絶対防御展開中！', 45, 50); }}
                
                ctx.fillStyle = '#555'; ctx.fillRect(610, 20, 250, 15);
                ctx.fillStyle = '#1c83e1'; ctx.fillRect(610, 20, (e_hp / e_max) * 250, 15);
                ctx.fillStyle = '#fff'; ctx.fillText('敵軍HP: ' + Math.max(0, Math.floor(e_hp)), 615, 32);
            }}

            // 💡 【スキル反映：ケイト】開幕先制5連撃
            if ("{p_skill_id}" === "lightning_raid") {{
                for(let k=0; k<5; k++) {{
                    bullets.push({{x: p_x + 50 + (k*20), y: p_y + (k*10-20), vx: 8, vy: 0, max_x: p_x + p_range_val, side: 'p', color: 'cyan', is_crit: false}});
                }}
            }}

            function animate() {{
                if (battleOver) return;
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                drawHPBars();
                
                // 💡 【スキル反映：レオニダス】HP30%以下で5秒間無敵化
                if ("{p_skill_id}" === "spartan_wall" && !p_immune_used && (p_hp / p_max) <= 0.3) {{
                    p_is_immune = true;
                    p_immune_used = true;
                    setTimeout(() => {{ p_is_immune = false; }}, 5000); // 5秒後に解除
                }}
                
                let current_distance = Math.abs(e_x - p_x);
                if (current_distance > p_range_val && p_x < e_x - 50) {{ p_x += p_speed; }}
                if (current_distance > e_range_val && e_x > p_x + 50) {{ e_x -= e_speed; }}
                
                // 描画
                ctx.fillStyle = p_is_immune ? 'yellow' : '{p_color}';
                ctx.beginPath(); ctx.arc(p_x, p_y, 25, 0, Math.PI*2); ctx.fill();
                ctx.fillStyle = '#fff'; ctx.font = '14px sans-serif'; ctx.fillText('🔴', p_x-8, p_y+4);
                
                ctx.fillStyle = '{e_color}';
                ctx.beginPath(); ctx.arc(e_x, e_y, 25, 0, Math.PI*2); ctx.fill();
                ctx.fillStyle = '#fff'; ctx.font = '14px sans-serif'; ctx.fillText('🔵', e_x-8, e_y+4);
                
                // プレイヤー通常発射
                if(Math.random() < p_fire_rate && p_hp > 0) {{
                    // 💡 【スキル反映：あかね】弾速アップ(通常7→11)
                    let bullet_vx = ("{p_skill_id}" === "crimson_drive") ? 11 : 7;
                    // 💡 【スキル反映：あいり】15%の確率でクリティカル弾
                    let is_crit = ("{p_skill_id}" === "gale_strike" && Math.random() < 0.15);
                    let b_color = is_crit ? 'gold' : '{p_color}';
                    bullets.push({{x: p_x + 25, y: p_y + (Math.random()*20-10), vx: bullet_vx, vy: 0, max_x: p_x + p_range_val, side: 'p', color: b_color, is_crit: is_crit}});
                }}
                
                // 敵発射
                if(Math.random() < e_fire_rate && e_hp > 0) {{
                    if ("{e_skill_id}" === "thunder_bolt") {{ // ゼウス 3way
                        bullets.push({{x: e_x - 25, y: e_y, vx: -7, vy: 0, max_x: e_x - e_range_val, side: 'e', color: 'yellow', size: 5}});
                        bullets.push({{x: e_x - 25, y: e_y, vx: -7, vy: -1.5, max_x: e_x - e_range_val, side: 'e', color: 'yellow', size: 5}});
                        bullets.push({{x: e_x - 25, y: e_y, vx: -7, vy: 1.5, max_x: e_x - e_range_val, side: 'e', color: 'yellow', size: 5}});
                    }} else {{
                        // 💡 【スキル反映：ナポレオン】弾のサイズを大きく(5→12)
                        let b_size = ("{e_skill_id}" === "artillery_god") ? 12 : 5;
                        bullets.push({{x: e_x - 25, y: e_y + (Math.random()*20-10), vx: -7, vy: 0, max_x: e_x - e_range_val, side: 'e', color: '{e_color}', size: b_size}});
                    }}
                }}
                
                // 弾丸ループ
                for(let i = bullets.length - 1; i >= 0; i--) {{
                    let b = bullets[i];
                    b.x += b.vx;
                    b.y += b.vy;
                    
                    let size = b.size || 5;
                    ctx.fillStyle = b.color;
                    ctx.beginPath(); ctx.arc(b.x, b.y, size, 0, Math.PI*2); ctx.fill();
                    
                    if((b.vx > 0 && b.x > b.max_x) || (b.vx < 0 && b.x < b.max_x) || b.y < 0 || b.y > canvas.height) {{
                        bullets.splice(i, 1); continue;
                    }}
                    
                    // プレイヤーの弾が敵にヒット
                    if(b.side === 'p' && Math.abs(b.x - e_x) <= (25 + size/2) && Math.abs(b.y - e_y) <= 25) {{
                        // 💡 【スキル反映：マリー】30%で敵が弾を完全無効化
                        if ("{e_skill_id}" === "royal_splendor" && Math.random() < 0.3) {{
                            bullets.splice(i, 1); continue;
                        }}
                        
                        let damage = p_atk_val * (0.8 + Math.random()*0.4);
                        if (b.is_crit) {{ damage *= 2; }} // クリティカル2倍
                        e_hp -= damage;
                        
                        // 💡 【スキル反映：アレクサンダー】ヒット時に敵を15px後方退避（ノックバック）
                        if ("{p_skill_id}" === "phalanx_push" && e_x < 850) {{ e_x += 15; }}
                        
                        bullets.splice(i, 1);
                        if(e_hp <= 0) {{ endBattle('WIN'); break; }}
                        continue;
                    }}
                    
                    // 敵の弾がプレイヤーにヒット
                    if(b.side === 'e' && Math.abs(b.x - p_x) <= (25 + size/2) && Math.abs(b.y - p_y) <= 25) {{
                        // 💡 【スキル反映：レオニダス】無敵時間ならダメージ1
                        let damage = p_is_immune ? 1 : (e_atk_val * (0.8 + Math.random()*0.4));
                        p_hp -= damage;
                        bullets.splice(i, 1);
                        if(p_hp <= 0) {{ endBattle('LOSE'); break; }}
                        continue;
                    }}
                }}
                requestAnimationFrame(animate);
            }}

            function endBattle(result) {{
                battleOver = true;
                document.getElementById('statusText').innerText = result === 'WIN' ? '🎉 WIN！敵部隊の撃破を確認しました！' : '💀 LOSE... 我軍の壊滅を確認しました。';
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
           if st.button("🏆 我軍の勝利(WIN)を確定させる", use_container_width=True):
                b_info = st.session_state.battle_info
                target_node = b_info["target_node"]
                enemy_uid = b_info["enemy_uid"]
                player_uid = b_info["player_uid"]
                
                # 1. 勝利したプレイヤー部隊の生存処理（アーサースキルなど）
                p_unit = st.session_state.units[player_uid]
                if p_unit["captain"].get("skill_id") == "avalon_bless":
                    p_unit["count"] += 1
                    add_log("🛡️ スキル【円卓の加護】で兵士が1名復帰。")
                    
                # 2. 💡 倒された敵の1部隊「だけ」をプールから削除
                if enemy_uid in st.session_state.units:
                    del st.session_state.units[enemy_uid]
                
                # 3. 💡 まだ同じマスに別の敵部隊が残っているかチェック
                remaining_enemies = [
                    u for u in st.session_state.units.values()
                    if u["node"] == target_node and u["owner"] != "プレイヤー(赤)"
                ]
                
                if len(remaining_enemies) > 0:
                    # まだ残党がいる場合：マスは占領せず、ログで警告
                    add_log(f"💥 撃破完了！しかし、{target_node} にはまだ敵の増援が {len(remaining_enemies)} 部隊残っています！")
                else:
                    # 敵が全滅した場合：ここで初めて領地をプレイヤーのものにする
                    st.session_state.nodes[target_node]["owner"] = "プレイヤー(赤)"
                    add_log(f"🚩 {target_node} の敵を完全に一掃し、領地を占領しました！")
                
                # 状態をリセットして侵攻フェーズへ
                st.session_state.phase = "侵攻"
                st.rerun()
                
        with col_l:
            if st.button("💀 我軍の敗北(LOSE)を受け入れる", use_container_width=True):
                b_info = st.session_state.battle_info
                player_uid = b_info["player_uid"]
                
                # プレイヤー部隊の消滅
                if player_uid in st.session_state.units:
                    add_log(f"😭 {st.session_state.units[player_uid]['captain']['name']}隊が全滅しました...")
                    del st.session_state.units[player_uid]
                    
                # 状態をリセットして侵攻フェーズへ
                st.session_state.phase = "侵攻"
                st.rerun()