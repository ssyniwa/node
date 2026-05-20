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
# 💡 【新設】ゲームデータを初期値にリセットする関数
def reset_game():
    
    st.session_state.map_generated = True
    st.session_state.phase = "資金確保"
    st.session_state.turn = 1
    st.session_state.selected_node = None     # 選択ノード
    st.session_state.selected_my_unit = None  # 選択自軍部隊
    st.session_state.battle_info = None       # 戦闘情報
    st.session_state.logs = ["🎮 ゲームが初期化されました！新たな戦いが始まります。"]
    st.session_state.country_data = {
        "プレイヤー(赤)": {"gold": 500, "captains": []},
        "AI(青)": {"gold": 300, "captains": []},
        "AI(緑)": {"gold": 300, "captains": []},
    }
    
    st.session_state.units = {}
    # 💡 【重要】AI部隊の元データをセッション状態に確実に保存する
    st.session_state.ai_unit_pool = AI_UNIT_POOL

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
    """
    AIの思考・行動ルーチン（部隊作成 ＋ 侵攻・戦闘処理）。
    COLORSの定義（"AI(青)", "AI(緑)"）に完全準拠しています。
    """
    add_log("🤖 AI軍のターンが開始されました。軍事戦略を立案中...")
    
    # ----------------------------------------------------------------=========
    # 🛠️ 1. AIの部隊作成（雇用）フェーズ
    # ----------------------------------------------------------------=========
    # 💡 COLORSのキー名と完全に一致させました
    ai_factions = ["AI(青)", "AI(緑)"]
    
    for faction in ai_factions:
        # このAI勢力が支配している領地をリストアップ
        my_nodes = [nid for nid, n in st.session_state.nodes.items() if n["owner"] == faction]
        
        if my_nodes:
            # 支配領地数に応じた雇用確率（20%〜50%）
            spawn_chance = 1.0            
            if random.random() < spawn_chance:
                # 現在部隊が駐留していない「空き領地」を探す
                occupied_nodes = {u["location"] for u in st.session_state.units.values()}
                empty_my_nodes = [nid for nid in my_nodes if nid not in occupied_nodes]
                
                if empty_my_nodes:
                    spawn_node = random.choice(empty_my_nodes)
                    
                    # セッション内のプールからランダム選出
                    if "ai_unit_pool" in st.session_state and st.session_state.ai_unit_pool:
                        template = random.choice(st.session_state.ai_unit_pool)
                    else:
                        template = {
                            "captain": {"name": "AI汎用将軍", "skill_id": "none", "skill_name": "なし", "skill_desc": ""},
                            "soldier_type": "歩兵部隊",
                            "count": 5
                        }
                    
                    new_uid = f"ai_unit_{random.randint(100000, 999999)}"
                    
                    # データをコピーして新規雇用部隊を配置
                    st.session_state.units[new_uid] = {
                        "owner": faction,
                        "location": spawn_node,
                        "count": template["count"],
                        "moved": False, 
                        "is_new": True, # 今ターン生成された目印
                        "captain": template["captain"].copy(),
                        "soldier_type": template["soldier_type"]
                    }
                    
                    add_log(f"💂‍♂️ 【AI徴兵】{faction}が {spawn_node} にて新将軍【{template['captain']['name']}】を招聘！"
                            f"{template['soldier_type']}（x{template['count']}）を結成しました。")

    # ----------------------------------------------------------------=========
    # 🏹 2. AIの部隊進軍・衝突フェーズ
    # ----------------------------------------------------------------=========
    # 💡 【重要】"AI軍" という文字の検索を廃止し、「プレイヤー(赤)以外」をすべてAI部隊として安全に一括取得
    all_ai_units = {
        uid: u for uid, u in st.session_state.units.items() 
        if u["owner"] != "プレイヤー(赤)"
    }
    
    # マップ上に活動可能なAI部隊が本当に1つもない場合のみガード
    if not all_ai_units:
        add_log("🏳️ マップ上に活動可能なAI部隊が1つも存在しません。次のターンに移ります。")
        st.session_state.phase = "資金確保"
        st.session_state.turn += 1
        st.rerun()
        return
    # 実際に動かせる部隊の処理ループ
    for ai_uid, ai_unit in all_ai_units.items():
        
        # 今ターン新規雇用された部隊（is_new）、または既に行動済みの部隊は移動させない
        if ai_unit.get("is_new") or ai_unit.get("moved"):
            continue
            
        ai_owner = ai_unit["owner"]
        current_loc = ai_unit["location"]
        adjacent_nodes = st.session_state.nodes[current_loc]["adjacent"]

        # 70%の確率で隣接領地への進軍を試みる
        if adjacent_nodes and random.random() < 0.9:
            target_node = random.choice(adjacent_nodes)
            
            # 【衝突検知】移動先に「自分（例:AI(青)）とは異なる勢力」がいるかチェック
            enemy_units_in_node = [
                {"id": uid, "data": u} for uid, u in st.session_state.units.items()
                if u["location"] == target_node and u["owner"] != ai_owner
            ]
            
            if len(enemy_units_in_node) > 0:
                # ==========================================================
                # 🔥 パターンA：防衛部隊と衝突！（戦場フェーズへ強制突入）
                # ==========================================================
                active_enemy = enemy_units_in_node[0] # 先頭の1部隊をロックオン
                enemy_uid = active_enemy["id"]
                e_unit = active_enemy["data"]
                
                # 戦闘情報をセッションに完全固定
                st.session_state.battle_info = {
                    "player_uid": enemy_uid,           # 防衛側
                    "enemy_uid": ai_uid,               # 攻撃側（攻めてきたAI部隊）
                    "player_unit_name": f"{e_unit['captain']['name']}隊({e_unit['owner']})",
                    "enemy_unit_name": f"{ai_unit['captain']['name']}隊({ai_owner})",
                    "target_node": target_node
                }
                
                # 攻めてきたAI部隊の位置を更新し、行動済みにする
                st.session_state.units[ai_uid]["location"] = target_node
                st.session_state.units[ai_uid]["moved"] = True
                
                # フラグを一括リフレッシュしてから戦闘画面へ
                _cleanup_ai_flags()
                
                st.session_state.phase = "戦場フェーズ"
                add_log(f"💥 【急報】{target_node} にて {ai_owner} の【{ai_unit['captain']['name']}隊】が侵攻！ "
                        f"待ち構える {e_unit['owner']} の【{e_unit['captain']['name']}隊】と激突、戦闘に入ります！")
                st.rerun()
                return 
                
            else:
                # ==========================================================
                # 🕊️ パターンB：無人の領地（通常移動、または無血占領）
                # ==========================================================
                st.session_state.units[ai_uid]["location"] = target_node
                st.session_state.units[ai_uid]["moved"] = True
                
                # 領地の支配権を塗り替える
                if st.session_state.nodes[target_node]["owner"] != ai_owner:
                    st.session_state.nodes[target_node]["owner"] = ai_owner
                    add_log(f"🚩 【AI領土拡大】{ai_owner} が無人の {target_node} を無血占領しました。")
                else:
                    add_log(f"🚚 【AI移動】{ai_owner} の {ai_unit['captain']['name']}隊 が {current_loc} から {target_node} へ移動しました。")
                
                # 💡 【重要】ここではリターンせず、次のAI部隊の行動処理へループを継続させる
                continue

    # 平和にAIターンが終了した場合のクリーンアップ
    _cleanup_ai_flags()
    add_log("🤖 AI軍の全作戦行動が完了しました。次のターン（資金確保フェーズ）に移ります。")
    
    # 💡 【重要】AIターン終了時にフェーズを戻し、ターンを進める処理を追加
    st.session_state.phase = "資金確保"
    st.session_state.turn += 1
    st.rerun()

def _cleanup_ai_flags():
    """AIターンの終了時に、プレイヤー以外の全部隊のフラグを一括リフレッシュ"""
    for u in st.session_state.units.values():
        if u["owner"] != "プレイヤー(赤)":
            u["moved"] = False   
            u["is_new"] = False
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
def safe_terminate_battle(atk_uid, dfn_uid, winner_uid=None):
    """部隊データの安全な削除とフェーズ遷移を保証する関数"""
    # 存在確認を行ってから削除する
    if winner_uid == atk_uid: # 攻撃側勝利
        if dfn_uid in st.session_state.units:
            del st.session_state.units[dfn_uid]
    elif winner_uid == dfn_uid: # 防衛側勝利
        if atk_uid in st.session_state.units:
            del st.session_state.units[atk_uid]
    else: # 引き分け（両方削除）
        if atk_uid in st.session_state.units: del st.session_state.units[atk_uid]
        if dfn_uid in st.session_state.units: del st.session_state.units[dfn_uid]

    # 状態の完全リセット
    st.query_params.clear()
    st.session_state.battle_info = None
    st.session_state.phase = "侵攻"
    st.rerun()
if "game_started" not in st.session_state:
    st.session_state.game_started = False
    reset_game()
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
                reset_game() # 💡 安全に初期化
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
                reset_game() # 💡 安全に初期化
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
                # 正しいデータ構造（country_data）からプレイヤーのゴールドを参照・更新する
                if st.session_state.country_data["プレイヤー(赤)"]["gold"] >= invest_cost:
                    st.session_state.country_data["プレイヤー(赤)"]["gold"] -= invest_cost
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


    elif st.session_state.phase == "侵攻":
        st.subheader("🏹 部隊侵攻・移動フェーズ")
        st.info("自軍の部隊を選択し、隣接する領地へ進軍（移動、または敵がいれば戦闘）させてください。")

        # 左右の2カラムに分割して、「動かす部隊」と「進軍先の領地」を綺麗に並べる
        col_unit, col_target = st.columns(2)

        # --- 1. 自軍部隊の選択（左カラム） ---
        with col_unit:
            my_units = {
                uid: u for uid, u in st.session_state.units.items()
                if u["owner"] == "プレイヤー(赤)"
            }
            
            if not my_units:
                st.warning("⚠️ 指揮できる自軍の部隊がありません。")
                st.session_state.selected_my_unit = None
            else:
                unit_options = {
                    uid: f"{u['captain']['name']}隊 ({u['location']} / 兵数:{u['count']})" + (" [行動済]" if u.get("moved") else " [未行動]")
                    for uid, u in my_units.items()
                }
                
                if "selected_my_unit" not in st.session_state or st.session_state.selected_my_unit not in my_units:
                    st.session_state.selected_my_unit = list(my_units.keys())[0]
                    
                st.session_state.selected_my_unit = st.selectbox(
                    "💂‍♂️ 動かす自軍の部隊",
                    options=list(my_units.keys()),
                    format_func=lambda x: unit_options[x]
                )

        # --- 2. 進軍先ノード（領地）の選択（右カラム） ---
        with col_target:
            if not st.session_state.selected_my_unit:
                st.write("💂‍♂️ まずは左側で部隊を選択してください。")
            else:
                # 1. 選択されている部隊の「現在地」を取得
                p_uid = st.session_state.selected_my_unit
                current_loc = st.session_state.units[p_uid]["location"]
                
                # 💡 【ここがポイント】その現在地とつながっている（隣接している）ノードのリストだけを抽出！
                adjacent_nodes = st.session_state.nodes[current_loc]["adjacent"]
                
                if not adjacent_nodes:
                    st.error("🛑 この領地は孤立しているため、どこにも進軍できません！")
                    st.session_state.selected_node = None
                else:
                    # マップクリック等で選ばれたノードが、もし隣接リスト内にある場合はそれを初期値にする
                    clicked_node = st.session_state.get("selected_node", None)
                    default_index = adjacent_nodes.index(clicked_node) if clicked_node in adjacent_nodes else 0
                    
                    # 💡 隣接しているノードだけをドロップダウンに表示
                    st.session_state.selected_node = st.selectbox(
                        f"🗺️ 進軍先を選択（{current_loc} から隣接）",
                        options=adjacent_nodes,
                        index=default_index,
                        key="node_selector_widget"
                    )
                    
                    st.markdown(f"現在地: **{current_loc}** ➡️ 進軍先: **{st.session_state.selected_node}**")

        st.write("---")

        # --- 3. 進軍・移動ボタンの処理 ---
        # ガード処理：自軍の部隊が選ばれていない場合
        if not st.session_state.selected_my_unit:
            st.error("部隊が選択されていないため、進軍コマンドを実行できません。")
            
        else:
            target_node = st.session_state.selected_node      # 移動先（ドロップダウン/マップで選んだ領地）
            p_uid = st.session_state.selected_my_unit         # 動かす自軍の部隊ID
            p_unit = st.session_state.units[p_uid]            # 自軍の部隊データ
            current_loc = p_unit["location"]                  # 部隊の現在地

            # 🛑 【ルールチェック】すでに動かした部隊は進軍できない
            if p_unit.get("moved"):
                st.error("❌ この部隊は今ターンすでに行動済みです。他の部隊を選ぶか、ターンを終了してください。")
                
            # 🛑 【ルールチェック】現在地と同じマスには進軍できない
            elif current_loc == target_node:
                st.info(f"ℹ️ 現在 {p_unit['captain']['name']}隊 はすでに {target_node} に駐留しています。別の隣接領地を選んでください。")
                
            # 🛑 【ルールチェック】現在地と隣接していない領地には進軍できない
            elif target_node not in st.session_state.nodes[current_loc]["adjacent"]:
                st.error(f"❌ {target_node} は、現在地（{current_loc}）と隣接していないため進軍できません！")
                
            else:
                # 💡 すべての安全チェックを通過！進軍ボタンを表示
                if st.button(f"⚔️ {p_unit['captain']['name']}隊 を {target_node} へ進軍させる", use_container_width=True, type="primary"):
                    
                    # 移動先に「プレイヤー(赤)以外の敵部隊」がいるか確認
                    enemy_units_in_node = [
                        {"id": uid, "data": u} for uid, u in st.session_state.units.items()
                        if u["location"] == target_node and u["owner"] != "プレイヤー(赤)"
                    ]
                    
                    if len(enemy_units_in_node) > 0:
                        # ==========================================================
                        # 🔥 パターンA：敵の防衛部隊を検知（戦場フェーズへ！）
                        # ==========================================================
                        active_enemy = enemy_units_in_node[0]  # 【連戦仕様】リストの先頭を今回の対戦相手に固定
                        enemy_uid = active_enemy["id"]
                        e_unit = active_enemy["data"]
                        
                        # 戦闘情報をセッションに保存（誤爆防止）
                        st.session_state.battle_info = {
                            "player_uid": p_uid,
                            "enemy_uid": enemy_uid,
                            "player_unit_name": f"{p_unit['captain']['name']}隊",
                            "enemy_unit_name": f"{e_unit['captain']['name']}隊",
                            "target_node": target_node
                        }
                        
                        # プレイヤー部隊を戦場マスへ潜入させ、行動済みにする
                        st.session_state.units[p_uid]["location"] = target_node
                        st.session_state.units[p_uid]["moved"] = True
                        
                        # 戦場フェーズへ強制移行
                        st.session_state.phase = "戦場フェーズ"
                        add_log(f"⚔️ 【交戦勃発】{p_unit['captain']['name']}隊が {target_node} に突入！待ち構える {e_unit['captain']['name']}隊 と戦闘に入ります！")
                        st.rerun()
                        
                    else:
                        # ==========================================================
                        # 🕊️ パターンB：敵部隊がいない（無血開城・ただの移動）
                        # ==========================================================
                        st.session_state.units[p_uid]["location"] = target_node
                        st.session_state.units[p_uid]["moved"] = True
                        
                        # 移動先が「中立」または「敵の無人領地」なら支配権をプレイヤーに塗り替える
                        if st.session_state.nodes[target_node]["owner"] != "プレイヤー(赤)":
                            st.session_state.nodes[target_node]["owner"] = "プレイヤー(赤)"
                            add_log(f"🚩 【占領】{p_unit['captain']['name']}隊が、無人の {target_node} を無血占領しました！")
                        else:
                            add_log(f"🚚 【移動】{p_unit['captain']['name']}隊が {current_loc} から {target_node} へ移動しました。")
                            
                        st.rerun()

        st.write("---")

        # --- 4. ターン終了ボタン（AIに手番を渡す） ---
        if st.button("⏳ 全部隊の行動を終了してAIターンへ", use_container_width=True):
            add_log(f"💤 プレイヤーが第 {st.session_state.turn} ターンの行動を終了しました。")
            run_ai_turn()
            # プレイヤー部隊の移動フラグをリセットして次のターンへバトンタッチ
            for uid, u in st.session_state.units.items():
                if u["owner"] == "プレイヤー(赤)":
                    u["moved"] = False
                    
            st.session_state.turn += 1
            st.session_state.phase = "資金確保"  # 資金フェーズに戻る
            add_log(f"📢 ターン {st.session_state.turn} が開始されました。")
            st.rerun()

    # --- ⚔️ 6. 統合：戦場フェーズ（結果表示バグ完全修正版） ---
    elif st.session_state.phase == "戦場フェーズ":
        # --- 1. 戦闘情報の安全な読み込みとガード処理 ---
        if "battle_info" not in st.session_state or not st.session_state.battle_info:
            st.error("🚨 戦闘情報が見つかりません。マップへ戻ります。")
            st.session_state.phase = "侵攻"
            st.rerun()

        b_info = st.session_state.battle_info
        target_node = b_info["target_node"]
        atk_uid = b_info["enemy_uid"]   # 攻撃側
        dfn_uid = b_info["player_uid"]  # 防衛側

        # セーフティ：部隊の生存確認
        if atk_uid not in st.session_state.units or dfn_uid not in st.session_state.units:
            st.warning("⚠️ 戦闘を継続できない部隊データを確認しました。戦闘を終了します。")
            st.session_state.battle_info = None
            st.session_state.phase = "侵攻"
            st.rerun()

        atk_unit = st.session_state.units[atk_uid]
        dfn_unit = st.session_state.units[dfn_uid]

        st.title("⚔️ リアルタイム交戦スクリーン（戦場フェーズ）")
        st.subheader(f"舞台: {target_node}")

        # --- 2. 戦闘データ抽出 ---
        atk_soldier = atk_unit["soldier_type"]
        dfn_soldier = dfn_unit["soldier_type"]

        atk_max_hp = atk_unit["count"] * 10 + atk_unit.get("captain", {}).get("dfn", 10)
        dfn_max_hp = dfn_unit["count"] * 10 + dfn_unit.get("captain", {}).get("dfn", 10)

        atk_atk = SOLDIER_TYPES[atk_soldier]["atk"] + atk_unit.get("captain", {}).get("atk", 10)
        dfn_atk = SOLDIER_TYPES[dfn_soldier]["atk"] + dfn_unit.get("captain", {}).get("dfn", 10)

        atk_range = SOLDIER_TYPES[atk_soldier]["range"]
        dfn_range = SOLDIER_TYPES[dfn_soldier]["range"]

        atk_color = SOLDIER_TYPES[atk_soldier]["color"]
        dfn_color = SOLDIER_TYPES[dfn_soldier]["color"]

        # 左右のUI表示
        col_dfn_ui, col_vs, col_atk_ui = st.columns([2, 1, 2])
        with col_dfn_ui:
            st.markdown(f"### 🛡️ 防衛側: {b_info['player_unit_name']}")
            st.markdown(f"**隊長:** {dfn_unit['captain']['name']} (所属: {dfn_unit['owner']})")
            dfn_skill_id = dfn_unit["captain"].get("skill_id", "none")
            st.markdown(f"⚡ **スキル: {dfn_unit['captain'].get('skill_name', 'なし')}**")
            st.write(f"兵種: **{dfn_soldier}** (x{dfn_unit['count']})")

        with col_vs:
            st.markdown("<h2 style='text-align:center; color:#ff4b4b; margin-top:30px;'>VS</h2>", unsafe_allow_html=True)

        with col_atk_ui:
            st.markdown(f"### 🎯 攻撃側: {b_info['enemy_unit_name']}")
            st.markdown(f"**隊長:** {atk_unit['captain']['name']} (所属: {atk_unit['owner']})")
            atk_skill_id = atk_unit["captain"].get("skill_id", "none")
            st.markdown(f"⚡ **スキル: {atk_unit['captain'].get('skill_name', 'なし')}**")
            st.write(f"兵種: **{atk_soldier}** (x{atk_unit['count']})")

        # --- 3. URLクエリパラメータから勝敗シグナルを取得 ---
        query_params = st.query_params
        battle_result_signal = query_params.get("battle_result", None)

        # --- 4. メインコンテンツの分岐：交戦中 Canvas か リザルト表示か ---
        if battle_result_signal is None:
            st.info("🎮 交戦中... 自動で決着がつくと下に結果が表示されます。")

            # ==================================================================
            # 🎨 HTML5 Canvas + JavaScript（確実なURLパラメータ付与方式）
            # ==================================================================
            battle_canvas_html = f"""
            <div style="text-align: center; background: #222; padding: 15px; border-radius: 8px;">
                <canvas id="battleCanvas" width="900" height="350" style="background:#111111; border:3px solid #555; max-width:100%;"></canvas>
                <h3 id="statusText" style="color: #fff; font-family: sans-serif; margin-top: 10px;">激戦中... 🔥</h3>
            </div>
            
            <script>
                const canvas = document.getElementById('battleCanvas');
                const ctx = canvas.getContext('2d');

                let dfn_hp = {dfn_max_hp};
                let atk_hp = {atk_max_hp};
                const dfn_max = {dfn_max_hp};
                let atk_max = {atk_max_hp};

                if ("{atk_skill_id}" === "panzer_charge") {{ atk_max += 50; atk_hp += 50; }}
                if ("{dfn_skill_id}" === "panzer_charge") {{ dfn_hp += 50; }}

                let dfn_x = 80, dfn_y = 175;
                let atk_x = 820, atk_y = 175;

                let dfn_speed = 1.5;
                let atk_speed = 1.5;

                let dfn_range_val = {dfn_range};
                let atk_range_val = {atk_range};

                let dfn_fire_rate = 0.08;
                let atk_fire_rate = 0.08;

                let dfn_atk_val = {dfn_atk};
                let atk_atk_val = {atk_atk};

                let bullets = [];
                let battleOver = false;

                function drawHPBars() {{
                    ctx.fillStyle = '#555'; ctx.fillRect(40, 20, 250, 15);
                    ctx.fillStyle = '#00f060'; ctx.fillRect(40, 20, Math.max(0, (dfn_hp / dfn_max)) * 250, 15);
                    ctx.fillStyle = '#fff'; ctx.font = '12px sans-serif'; ctx.fillText('防衛軍HP: ' + Math.max(0, Math.floor(dfn_hp)), 45, 32);
                    
                    ctx.fillStyle = '#555'; ctx.fillRect(610, 20, 250, 15);
                    ctx.fillStyle = '#ff4b4b'; ctx.fillRect(610, 20, Math.max(0, (atk_hp / atk_max)) * 250, 15);
                    ctx.fillStyle = '#fff'; ctx.fillText('攻撃軍HP: ' + Math.max(0, Math.floor(atk_hp)), 615, 32);
                }}

                function animate() {{
                    if (battleOver) return;
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    drawHPBars();
                    
                    let current_distance = Math.abs(atk_x - dfn_x);
                    if (current_distance > dfn_range_val && dfn_x < atk_x - 50) {{ dfn_x += dfn_speed; }}
                    if (current_distance > atk_range_val && atk_x > dfn_x + 50) {{ atk_x -= atk_speed; }}
                    
                    ctx.fillStyle = '{dfn_color}';
                    ctx.beginPath(); ctx.arc(dfn_x, dfn_y, 25, 0, Math.PI*2); ctx.fill();
                    
                    ctx.fillStyle = '{atk_color}';
                    ctx.beginPath(); ctx.arc(atk_x, atk_y, 25, 0, Math.PI*2); ctx.fill();
                    
                    if(Math.random() < dfn_fire_rate && dfn_hp > 0) {{
                        bullets.push({{x: dfn_x + 25, y: dfn_y, vx: 7, vy: 0, max_x: dfn_x + dfn_range_val, side: 'dfn', color: '{dfn_color}'}});
                    }}
                    
                    if(Math.random() < atk_fire_rate && atk_hp > 0) {{
                        bullets.push({{x: atk_x - 25, y: atk_y, vx: -7, vy: 0, max_x: atk_x - atk_range_val, side: 'atk', color: '{atk_color}'}});
                    }}
                    
                    for(let i = bullets.length - 1; i >= 0; i--) {{
                        let b = bullets[i]; b.x += b.vx;
                        ctx.fillStyle = b.color;
                        ctx.beginPath(); ctx.arc(b.x, b.y, 5, 0, Math.PI*2); ctx.fill();
                        
                        if((b.vx > 0 && b.x > b.max_x) || (b.vx < 0 && b.x < b.max_x)) {{
                            bullets.splice(i, 1); continue;
                        }}
                        
                        if(b.side === 'dfn' && Math.abs(b.x - atk_x) <= 30) {{
                            atk_hp -= dfn_atk_val * (0.8 + Math.random()*0.4);
                            bullets.splice(i, 1);
                            if(atk_hp <= 0) {{ endBattle('atk_lose'); break; }} // 攻撃側死亡＝防衛勝利
                            continue;
                        }}
                        
                        if(b.side === 'atk' && Math.abs(b.x - dfn_x) <= 30) {{
                            dfn_hp -= atk_atk_val * (0.8 + Math.random()*0.4);
                            bullets.splice(i, 1);
                            if(dfn_hp <= 0) {{ endBattle('atk_win'); break; }}  // 防衛側死亡＝攻撃勝利
                            continue;
                        }}
                    }}
                    requestAnimationFrame(animate);
                }}

                function endBattle(result) {{
                    if (battleOver) return;
                    battleOver = true;
                    document.getElementById('statusText').innerText = '🏳️ 合戦決着！結果を反映中...';
                    
                    // 💡 URLに直接パラメータを載せて親画面に確実に伝える
                    setTimeout(() => {{
                        const currentUrl = new URL(window.parent.location.href);
                        currentUrl.searchParams.set('battle_result', result);
                        window.parent.location.href = currentUrl.toString();
                    }}, 500);
                }}

                animate();
            </script>
            """
            components.html(battle_canvas_html, height=430)
            
        else:
            # ==================================================================
            # 🏁 決着リザルト表示画面（パラメータ検知によりここで確実にストップ）
            # ==================================================================
            st.header("📋 合戦最終戦果報告")

            # battle_result_signal に格納された勝敗データに基づいて条件分岐
            if battle_result_signal == "atk_win":
                winner_owner = atk_unit["owner"]
                winner_name = b_info["enemy_unit_name"]
                loser_name = b_info["player_unit_name"]
                
                st.error(f"⚔️ **【敗北】AI側：{winner_name}** が占領に成功しました。")
                st.caption(f"🛡️ プレイヤー側：{loser_name} の守備隊は全滅しました...")
                
                if st.button("敗戦報告を確認してマップへ戻る", use_container_width=True, type="primary"):
                    # データを安全に反映してからマップへ戻る
                    
                    st.session_state.nodes[target_node]["owner"] = winner_owner
                    add_log(f"⚔️ 【占領】{target_node} が {winner_name} に占領されました。")
                    safe_terminate_battle(atk_uid, dfn_uid, winner_uid=atk_uid)

            elif battle_result_signal == "dfn_win":
                winner_owner = dfn_unit["owner"]
                winner_name = b_info["player_unit_name"]
                loser_name = b_info["enemy_unit_name"]
                
                st.success(f"🛡️ **【防衛成功】プレイヤー側：{winner_name}** が領地を死守しました！")
                st.markdown(f"💀 AI側：{loser_name} の侵略軍は返り討ちにあい、全滅しました。")
                
                if st.button("防衛報告を確認してマップへ戻る", use_container_width=True, type="primary"):
                    # スキル処理
                    if winner_owner == "プレイヤー(赤)" and dfn_unit["captain"].get("skill_id") == "avalon_bless":
                        st.session_state.units[dfn_uid]["count"] += 1
                        add_log("🛡️ スキル【円卓の加護】が発動！負傷兵が1名復帰しました。")
                    
                    
                        
                    add_log(f"🛡️ 【戦果】{winner_name} が見事に【{target_node}】の守備に成功しました。")
                    
                    safe_terminate_battle(atk_uid, dfn_uid, winner_uid=dfn_uid)
            

            